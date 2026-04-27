from __future__ import annotations

import json
from typing import Any

from openai import AzureOpenAI, BadRequestError, OpenAI
from pydantic import BaseModel, Field

from .config import Settings


class CypherPlan(BaseModel):
    cypher: str = Field(description="A single read-only Cypher query.")
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", description="Brief reason for the query shape.")


CYPHER_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "cypher": {
            "type": "string",
            "description": "A single read-only Cypher query that answers the user question.",
        },
        "parameters": {
            "type": "object",
            "description": "Cypher query parameters as a JSON object.",
            "additionalProperties": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "integer"},
                    {"type": "boolean"},
                    {"type": "null"},
                    {
                        "type": "array",
                        "items": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "number"},
                                {"type": "integer"},
                                {"type": "boolean"},
                                {"type": "null"},
                            ]
                        },
                    },
                ]
            },
        },
        "reason": {
            "type": "string",
            "description": "One short sentence explaining how the query answers the question.",
        },
    },
    "required": ["cypher", "parameters", "reason"],
    "additionalProperties": False,
}


CYPHER_FEW_SHOTS = """
Use these examples as style guides. Adapt labels and properties only when they exist in the provided schema.

Question: Which drugs treat diseases affecting humans?
JSON:
{
  "cypher": "MATCH (d:Drug)-[:TREATS]->(dis:Disease)-[:AFFECTS]->(o:Organism) WHERE toLower(o.type) = toLower($organismType) RETURN d.name AS drugName, dis.name AS diseaseName",
  "parameters": {"organismType": "human"},
  "reason": "Find drugs connected to diseases that affect the requested organism."
}

Question: What compound is produced by C + O2?
JSON:
{
  "cypher": "MATCH (r:Reaction)-[:PRODUCT]->(c:Compound) WHERE toLower(r.equation) = toLower($equation) RETURN c.name AS compoundName, c.formula AS formula",
  "parameters": {"equation": "C + O2 -> CO2"},
  "reason": "Match the reaction equation and return its product compound."
}

Question: Which elements are reactants for methane?
JSON:
{
  "cypher": "MATCH (e:Element)-[rel:REACTANT]->(:Reaction)-[:PRODUCT]->(c:Compound) WHERE toLower(c.name) = toLower($compoundName) RETURN e.name AS elementName, e.symbol AS symbol, rel.ratio AS ratio",
  "parameters": {"compoundName": "methane"},
  "reason": "Follow reactant relationships into the reaction that produces the requested compound."
}

Question: Which drugs use carbon dioxide?
JSON:
{
  "cypher": "MATCH (c:Compound)-[:USED_IN]->(d:Drug) WHERE toLower(c.name) = toLower($compoundName) RETURN c.name AS compoundName, d.name AS drugName",
  "parameters": {"compoundName": "carbon dioxide"},
  "reason": "Find drugs connected to the requested compound through USED_IN."
}

Question: What organisms are affected by headache?
JSON:
{
  "cypher": "MATCH (dis:Disease)-[:AFFECTS]->(o:Organism) WHERE toLower(dis.name) = toLower($diseaseName) RETURN dis.name AS diseaseName, o.type AS organismType",
  "parameters": {"diseaseName": "headache"},
  "reason": "Find organisms connected to the requested disease through AFFECTS."
}
""".strip()


def _extract_response_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    if isinstance(response, dict):
        if response.get("output_text"):
            return str(response["output_text"])
        output = response.get("output", [])
    else:
        output = getattr(response, "output", [])

    parts: list[str] = []
    for item in output or []:
        content = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", [])
        for part in content or []:
            if isinstance(part, dict):
                text = part.get("text")
            else:
                text = getattr(part, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(parts).strip()


def _extract_chat_output_text(completion: Any) -> str:
    choices = completion.get("choices", []) if isinstance(completion, dict) else completion.choices
    if not choices:
        return ""

    choice = choices[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else choice.message
    content = message.get("content", "") if isinstance(message, dict) else message.content

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
            else:
                text = getattr(item, "text", None) or getattr(item, "content", None)
            if text:
                parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content or "")


def _parse_cypher_plan(raw_text: str) -> CypherPlan:
    try:
        return CypherPlan.model_validate_json(raw_text)
    except Exception:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise
        return CypherPlan.model_validate(json.loads(raw_text[start : end + 1]))


class OpenAIGraphAssistant:
    def __init__(self, *, client: OpenAI, model: str, api_mode: str = "responses") -> None:
        self.client = client
        self.model = model
        self.api_mode = api_mode

    def generate_cypher(
        self,
        *,
        question: str,
        schema_summary: str,
        history: list[dict[str, str]] | None = None,
    ) -> CypherPlan:
        instructions = (
            "You generate read-only Neo4j Cypher for a chemistry graph. "
            "Use only the schema provided by the app. Return exactly one query. "
            "Do not use CREATE, MERGE, SET, DELETE, REMOVE, DROP, LOAD CSV, CALL, or multiple statements. "
            "Use parameters for dynamic values. Include RETURN columns with clear names. "
            "Neo4j string comparisons are case-sensitive. For user-provided string filters, prefer "
            "WHERE toLower(node.property) = toLower($parameter) instead of property maps such as "
            "(node:Label {property: $parameter}). If sample values clearly answer the case, use that exact value. "
            f"{CYPHER_FEW_SHOTS} "
            "Return only JSON with cypher, parameters, and reason."
        )
        payload = {
            "question": question,
            "schema": schema_summary,
            "recent_chat_history": (history or [])[-6:],
        }

        if self.api_mode == "chat_completions":
            return self._generate_cypher_with_chat_completions(instructions, payload)

        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=True),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "cypher_plan",
                    "strict": True,
                    "schema": CYPHER_PLAN_SCHEMA,
                }
            },
        )
        return _parse_cypher_plan(_extract_response_output_text(response))

    def summarize_answer(
        self,
        *,
        question: str,
        cypher: str,
        rows: list[dict[str, Any]],
    ) -> str:
        if not rows:
            return "I could not find any matching records in the graph."

        instructions = (
            "Answer the user's graph question using only the rows supplied by the database. "
            "Be concise, mention when the result is based on the returned rows, and do not invent facts."
        )
        payload = {
            "question": question,
            "cypher": cypher,
            "rows": rows,
        }

        if self.api_mode == "chat_completions":
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
                ],
            )
            text = _extract_chat_output_text(completion).strip()
            return text or "I found matching rows, but could not produce a summary."

        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=True),
        )
        text = _extract_response_output_text(response).strip()
        return text or "I found matching rows, but could not produce a summary."

    def _generate_cypher_with_chat_completions(
        self,
        instructions: str,
        payload: dict[str, Any],
    ) -> CypherPlan:
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "cypher_plan",
                "strict": True,
                "schema": CYPHER_PLAN_SCHEMA,
            },
        }

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=response_format,
            )
        except BadRequestError as exc:
            # Some Azure deployments support JSON mode before full JSON schema mode.
            # Keep the same parser and app-side Cypher guard after this fallback.
            if "json_schema" not in str(exc) and "response_format" not in str(exc):
                raise
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )

        return _parse_cypher_plan(_extract_chat_output_text(completion))


def build_graph_assistant(settings: Settings) -> OpenAIGraphAssistant:
    if settings.openai_provider == "azure":
        client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        return OpenAIGraphAssistant(
            client=client,
            model=settings.azure_openai_deployment,
            api_mode="chat_completions",
        )

    return OpenAIGraphAssistant(
        client=OpenAI(api_key=settings.openai_api_key),
        model=settings.openai_model,
    )
