Extract the most relevant graph search terms from a user question about a research paper.

Return only valid JSON with this shape:
{
  "entities": ["Artificial Intelligence"],
  "concepts": ["Academic Performance"],
  "keywords": ["privacy"]
}

Rules:
- Include entity or concept names that should match graph nodes.
- Include short keywords only when named entities are not obvious.
- Prefer terms from the question; do not answer the question.
- Normalize "AI" to "Artificial Intelligence".
- Preserve important research terms such as "academic performance", "data privacy", "virtual assistants", "questionnaire", and percentages.
- Return at most 8 total terms across all arrays.
