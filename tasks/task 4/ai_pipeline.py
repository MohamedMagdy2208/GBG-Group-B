"""
AI Processing Pipeline for the Lost & Found system.

Uses Azure AI services (OpenAI, Vision, AI Search) for:
- Extracting structured attributes from free text
- Analyzing item images
- Generating embeddings
- Indexing and searching in Azure AI Search
- Reasoning about match confidence

Falls back to realistic mock responses when Azure credentials are not configured.
"""

import json
import os
import random
from datetime import datetime
from typing import Optional
from uuid import uuid4

import config

# ─── Prompt loading ──────────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(config.PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─── Azure OpenAI client (lazy init) ────────────────────────────────

_openai_client = None


def _get_openai_client():
    """Return a cached Azure OpenAI client."""
    global _openai_client
    if _openai_client is None:
        from openai import AzureOpenAI
        _openai_client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )
    return _openai_client


# ═══════════════════════════════════════════════════════════════════
# 1. EXTRACT ITEM ATTRIBUTES
# ═══════════════════════════════════════════════════════════════════

def extract_item_attributes(description: str) -> dict:
    """
    Extract structured attributes from a free-text item description using GPT-4o.

    Input:  "I lost my scratched silver laptop near gate B12 yesterday"
    Output: {
        "category": "laptop",
        "color": "silver",
        "brand": "unknown",
        "distinctive_features": ["scratched surface"],
        "location_hint": "gate B12",
        "normalized_description": "silver laptop with scratched surface"
    }
    """
    if config.is_demo_mode():
        return _mock_extract_attributes(description)

    try:
        prompt_template = _load_prompt("attribute_extraction.txt")
        prompt = prompt_template.replace("{description}", description)

        client = _get_openai_client()
        response = client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT_GPT4O,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw) if isinstance(raw, str) else {}
        if not isinstance(result, dict):
            result = {}
        # Ensure all expected keys exist
        result.setdefault("category", "other")
        result.setdefault("color", "unknown")
        result.setdefault("brand", "unknown")
        result.setdefault("distinctive_features", [])
        if not isinstance(result["distinctive_features"], list):
            result["distinctive_features"] = []
        result.setdefault("normalized_description", description)
        return result
    except Exception as e:
        return {
            "category": "other",
            "color": "unknown",
            "brand": "unknown",
            "distinctive_features": [],
            "normalized_description": description,
            "error": str(e),
        }


def _mock_extract_attributes(description: str) -> dict:
    """Generate mock structured attributes from description keywords."""
    desc_lower = description.lower()

    # Simple keyword-based category detection
    category_map = {
        "wallet": "wallet", "billfold": "wallet", "purse": "wallet",
        "laptop": "laptop", "macbook": "laptop", "notebook": "laptop",
        "phone": "phone", "iphone": "phone", "samsung": "phone", "mobile": "phone",
        "watch": "watch", "rolex": "watch", "timepiece": "watch",
        "bag": "bag", "backpack": "bag", "handbag": "bag",
        "luggage": "luggage", "suitcase": "luggage", "trolley": "luggage",
        "passport": "passport",
        "key": "keys", "keys": "keys",
        "headphone": "headphones", "airpod": "headphones", "earbud": "headphones",
        "camera": "camera",
        "glasses": "glasses", "sunglasses": "glasses",
        "umbrella": "umbrella",
        "charger": "charger",
        "jewelry": "jewelry", "ring": "jewelry", "necklace": "jewelry", "bracelet": "jewelry",
    }
    category = "other"
    for keyword, cat in category_map.items():
        if keyword in desc_lower:
            category = cat
            break

    # Color detection
    colors = ["black", "white", "red", "blue", "green", "silver", "gold", "brown",
              "gray", "grey", "pink", "navy", "titanium", "beige"]
    color = "unknown"
    for c in colors:
        if c in desc_lower:
            color = c
            break

    # Brand detection
    brands = ["apple", "samsung", "sony", "rolex", "montblanc", "samsonite", "nike",
              "adidas", "gucci", "louis vuitton", "prada", "dell", "hp", "lenovo"]
    brand = "unknown"
    for b in brands:
        if b in desc_lower:
            brand = b.title()
            break

    # Distinctive features
    features = []
    feature_keywords = {
        "scratch": "scratched surface", "crack": "cracked", "broken": "broken/damaged",
        "sticker": "has stickers", "engrav": "engraved", "dent": "dented",
        "torn": "torn/ripped", "faded": "faded color", "keychain": "has keychain attached",
        "ribbon": "has ribbon", "tag": "has tag/label",
    }
    for keyword, feature in feature_keywords.items():
        if keyword in desc_lower:
            features.append(feature)

    return {
        "category": category,
        "color": color,
        "brand": brand,
        "distinctive_features": features,
        "normalized_description": f"{color} {category}" + (f" by {brand}" if brand != "unknown" else "")
                                  + (f" with {', '.join(features)}" if features else ""),
    }


# ═══════════════════════════════════════════════════════════════════
# 2. ANALYZE ITEM IMAGE
# ═══════════════════════════════════════════════════════════════════

def analyze_item_image(image_path: str) -> dict:
    """
    Analyze a found item image using Azure AI Vision (Image Analysis 4.0).

    Returns: tags, detected objects, OCR text, dominant colors, brand hints.
    """
    if not config.is_vision_available():
        return _mock_analyze_image(image_path)

    try:
        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures
        from azure.core.credentials import AzureKeyCredential

        client = ImageAnalysisClient(
            endpoint=config.AZURE_VISION_ENDPOINT,
            credential=AzureKeyCredential(config.AZURE_VISION_KEY),
        )

        with open(image_path, "rb") as f:
            image_data = f.read()

        result = client.analyze(
            image_data=image_data,
            visual_features=[
                VisualFeatures.TAGS,
                VisualFeatures.OBJECTS,
                VisualFeatures.READ,
                VisualFeatures.CAPTION,
                VisualFeatures.DENSE_CAPTIONS,
            ],
        )

        tags = [tag.name for tag in (result.tags.list if result.tags else [])]
        objects_detected = [obj.tags[0].name for obj in (result.objects.list if result.objects else []) if obj.tags]
        ocr_text = ""
        if result.read and result.read.blocks:
            ocr_text = " ".join(
                line.text for block in result.read.blocks for line in block.lines
            )
        caption = result.caption.text if result.caption else ""

        return {
            "tags": tags,
            "objects": objects_detected,
            "ocr_text": ocr_text,
            "caption": caption,
            "dominant_colors": [],  # Vision 4.0 uses tags for color
            "brand_hints": [t for t in tags if t[0].isupper()] if tags else [],
        }
    except Exception as e:
        return _mock_analyze_image(image_path, error=str(e))


def _mock_analyze_image(image_path: str, error: str = "") -> dict:
    """Return mock image analysis results."""
    mock_results = [
        {
            "tags": ["wallet", "leather", "accessory", "black", "personal item"],
            "objects": ["wallet"],
            "ocr_text": "",
            "caption": "A black leather wallet on a table",
            "dominant_colors": ["black", "brown"],
            "brand_hints": [],
        },
        {
            "tags": ["electronics", "laptop", "computer", "silver", "sticker"],
            "objects": ["laptop"],
            "ocr_text": "MacBook Pro",
            "caption": "A silver laptop computer with stickers",
            "dominant_colors": ["silver", "gray"],
            "brand_hints": ["Apple", "MacBook"],
        },
        {
            "tags": ["watch", "gold", "luxury", "timepiece", "wristwatch"],
            "objects": ["watch"],
            "ocr_text": "ROLEX",
            "caption": "A gold wristwatch with minor scratches",
            "dominant_colors": ["gold"],
            "brand_hints": ["Rolex"],
        },
        {
            "tags": ["luggage", "suitcase", "blue", "travel", "wheels"],
            "objects": ["suitcase"],
            "ocr_text": "Samsonite",
            "caption": "A dark blue rolling suitcase with a red ribbon",
            "dominant_colors": ["blue", "navy"],
            "brand_hints": ["Samsonite"],
        },
        {
            "tags": ["earbuds", "case", "white", "electronics", "small"],
            "objects": ["earbuds case"],
            "ocr_text": "",
            "caption": "A white earbuds charging case with a keychain",
            "dominant_colors": ["white"],
            "brand_hints": ["Apple", "AirPods"],
        },
    ]
    result = random.choice(mock_results)
    if error:
        result["error"] = error
    return result


# ═══════════════════════════════════════════════════════════════════
# 3. GENERATE EMBEDDING
# ═══════════════════════════════════════════════════════════════════

def generate_embedding(text: str) -> list[float]:
    """
    Convert a text description into a 1536-dimensional vector embedding
    using text-embedding-3-small via Azure OpenAI.
    """
    if config.is_demo_mode():
        return _mock_embedding(text)

    try:
        client = _get_openai_client()
        response = client.embeddings.create(
            model=config.AZURE_OPENAI_DEPLOYMENT_EMBEDDING,
            input=text,
        )
        return response.data[0].embedding
    except Exception:
        return _mock_embedding(text)


def _mock_embedding(text: str) -> list[float]:
    """Generate a deterministic mock embedding vector (1536 dims)."""
    random.seed(hash(text) % (2**32))
    return [random.uniform(-1, 1) for _ in range(1536)]


# ═══════════════════════════════════════════════════════════════════
# 4. INDEX FOUND ITEM IN AZURE AI SEARCH
# ═══════════════════════════════════════════════════════════════════

def index_found_item(found_item: dict, attributes: dict, embedding: list[float]) -> bool:
    """
    Upload a found item with its AI-extracted attributes and embedding vector
    to Azure AI Search for hybrid retrieval.
    """
    if not config.is_search_available():
        return True  # Mock success in demo mode

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        client = SearchClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            index_name=config.AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY),
        )

        document = {
            "id": str(found_item.get("found_id", uuid4())),
            "item_type": "found",
            "category": attributes.get("category", "other"),
            "color": attributes.get("color", ""),
            "brand": attributes.get("brand", ""),
            "location": found_item.get("location_found", ""),
            "normalized_description": attributes.get("normalized_description", ""),
            "distinctive_features": attributes.get("distinctive_features", []),
            "timestamp": found_item.get("time_found", datetime.utcnow().isoformat()).replace("+00:00", "") + "Z",
            "embedding": embedding,
        }

        client.upload_documents(documents=[document])
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════
# 5. FIND MATCHES (HYBRID SEARCH + GPT-4o SCORING)
# ═══════════════════════════════════════════════════════════════════

def find_matches(lost_report: dict, found_items: list[dict], top_k: int = 5) -> list[dict]:
    """
    Search for matching found items given a lost item report.

    1. Generate embedding for lost item description
    2. Run hybrid search (vector + keyword) in Azure AI Search or local matching
    3. For each candidate, use GPT-4o to reason and score the match
    4. Return ranked list of match results with confidence scores

    In demo mode, performs local attribute-based matching against found_items from the DB.
    """
    if config.is_demo_mode() or not config.is_search_available():
        return _mock_find_matches(lost_report, found_items, top_k)

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.models import VectorizedQuery

        # Generate embedding for lost item
        lost_embedding = generate_embedding(lost_report.get("item_description", ""))

        client = SearchClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            index_name=config.AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY),
        )

        # Hybrid search: vector + keyword
        vector_query = VectorizedQuery(
            vector=lost_embedding,
            k_nearest_neighbors=top_k,
            fields="embedding",
        )

        results = client.search(
            search_text=lost_report.get("item_description", ""),
            vector_queries=[vector_query],
            top=top_k,
            filter="item_type eq 'found'",
        )

        matches = []
        lost_attrs = extract_item_attributes(lost_report.get("item_description", ""))

        for result in results:
            found_attrs = {
                "category": result.get("category", ""),
                "color": result.get("color", ""),
                "brand": result.get("brand", ""),
                "distinctive_features": result.get("distinctive_features", []),
                "normalized_description": result.get("normalized_description", ""),
            }

            reasoning = reason_about_match(
                lost_desc=lost_report.get("item_description", ""),
                found_desc=result.get("normalized_description", ""),
                lost_attrs=lost_attrs,
                found_attrs=found_attrs,
            )

            matches.append({
                "match_id": str(uuid4()),
                "lost_case_id": lost_report.get("case_id", ""),
                "found_item_id": result["id"],
                "confidence_score": reasoning.get("confidence_score", 0.0),
                "match_reasons": reasoning.get("matching_factors", []),
                "reasoning": reasoning.get("reasoning", ""),
                "recommendation": reasoning.get("recommendation", "REVIEW"),
            })

        matches.sort(key=lambda m: m["confidence_score"], reverse=True)
        if matches:
            return matches[:top_k]
        # Fall back to local matching if Azure Search returned no results
        return _mock_find_matches(lost_report, found_items, top_k)

    except Exception:
        return _mock_find_matches(lost_report, found_items, top_k)


def _mock_find_matches(lost_report: dict, found_items: list[dict], top_k: int = 5) -> list[dict]:
    """Generate mock match results using simple attribute comparison."""
    lost_desc = lost_report.get("item_description", "").lower()
    lost_category = lost_report.get("item_category", "other").lower()
    lost_color = lost_report.get("item_color", "").lower()
    lost_brand = lost_report.get("item_brand", "").lower()
    lost_location = lost_report.get("location_last_seen", "").lower()

    matches = []
    for item in found_items:
        if item.get("status") != "unclaimed":
            continue

        score = 0.0
        reasons = []
        contradictions = []

        found_category = item.get("item_category", "").lower()
        found_color = item.get("item_color", "").lower()
        found_brand = item.get("item_brand", "").lower()
        found_location = item.get("location_found", "").lower()
        found_desc = item.get("item_description", "").lower()

        # Category match (0.3 weight)
        if lost_category and found_category and lost_category == found_category:
            score += 0.30
            reasons.append(f"Category match: {lost_category}")
        elif lost_category and found_category and lost_category != found_category:
            contradictions.append(f"Category mismatch: {lost_category} vs {found_category}")

        # Color match (0.2 weight)
        color_synonyms = {
            "navy": "blue", "dark blue": "blue", "navy blue": "blue",
            "grey": "gray", "titanium": "gray", "silver": "gray",
            "dark gray": "gray", "dark grey": "gray",
        }
        norm_lost_color = color_synonyms.get(lost_color, lost_color)
        norm_found_color = color_synonyms.get(found_color, found_color)
        if norm_lost_color and norm_found_color:
            if norm_lost_color == norm_found_color or norm_lost_color in norm_found_color or norm_found_color in norm_lost_color:
                score += 0.20
                reasons.append(f"Color match: {lost_color} ~ {found_color}")
            else:
                contradictions.append(f"Color mismatch: {lost_color} vs {found_color}")

        # Brand match (0.2 weight)
        if lost_brand and found_brand and lost_brand != "unknown" and found_brand != "unknown":
            if lost_brand == found_brand or lost_brand in found_brand or found_brand in lost_brand:
                score += 0.20
                reasons.append(f"Brand match: {found_brand}")
            else:
                contradictions.append(f"Brand mismatch: {lost_brand} vs {found_brand}")
                score -= 0.10  # Penalty for brand contradiction

        # Location proximity (0.15 weight)
        if lost_location and found_location:
            if lost_location == found_location or lost_location in found_location:
                score += 0.15
                reasons.append(f"Same location: {found_location}")

        # Description keyword overlap (0.15 weight)
        lost_words = set(lost_desc.split())
        found_words = set(found_desc.split())
        common_words = lost_words & found_words
        # Remove common stop words
        stop_words = {"a", "an", "the", "with", "and", "or", "my", "i", "is", "it", "of", "in", "on", "at", "has", "had", "have"}
        meaningful_common = common_words - stop_words
        if meaningful_common:
            keyword_score = min(len(meaningful_common) * 0.03, 0.15)
            score += keyword_score
            reasons.append(f"Keyword overlap: {', '.join(list(meaningful_common)[:5])}")

        # Clamp score to [0.0, 1.0]
        score = max(0.0, min(score, 1.0))

        # Determine recommendation
        if score >= 0.85:
            recommendation = "CONFIRM"
        elif score >= 0.60:
            recommendation = "REVIEW"
        else:
            recommendation = "REJECT"

        reasoning = (
            f"Based on attribute comparison: category={'match' if lost_category == found_category else 'different'}, "
            f"color={'similar' if norm_lost_color == norm_found_color else 'different'}, "
            f"brand={'match' if lost_brand and found_brand and (lost_brand in found_brand or found_brand in lost_brand) else 'inconclusive'}, "
            f"location={'same area' if lost_location in found_location else 'different area'}. "
            f"Overall confidence: {score:.0%}."
        )

        matches.append({
            "match_id": str(uuid4()),
            "lost_case_id": lost_report.get("case_id", ""),
            "found_item_id": item.get("found_id", ""),
            "confidence_score": round(score, 2),
            "match_reasons": reasons,
            "contradicting_factors": contradictions,
            "reasoning": reasoning,
            "recommendation": recommendation,
        })

    matches.sort(key=lambda m: m["confidence_score"], reverse=True)
    return matches[:top_k]


# ═══════════════════════════════════════════════════════════════════
# 6. REASON ABOUT MATCH (GPT-4o)
# ═══════════════════════════════════════════════════════════════════

def reason_about_match(
    lost_desc: str,
    found_desc: str,
    lost_attrs: dict,
    found_attrs: dict,
    found_location: str = "",
    found_time: str = "",
) -> dict:
    """
    Use GPT-4o to act as an airport claims adjuster and reason about
    whether a lost item and found item are the same.

    Returns: {"confidence_score": 0.87, "reasoning": "...", "matching_factors": [...], ...}
    """
    if config.is_demo_mode():
        return _mock_reason(lost_attrs, found_attrs)

    try:
        prompt_template = _load_prompt("match_reasoning.txt")
        prompt = prompt_template.replace("{lost_description}", lost_desc) \
            .replace("{lost_attributes}", json.dumps(lost_attrs, indent=2)) \
            .replace("{found_description}", found_desc) \
            .replace("{found_attributes}", json.dumps(found_attrs, indent=2)) \
            .replace("{found_location}", found_location) \
            .replace("{found_time}", found_time)

        client = _get_openai_client()
        response = client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT_GPT4O,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw) if isinstance(raw, str) else {}
        if not isinstance(result, dict):
            result = {}
        result.setdefault("confidence_score", 0.0)
        result.setdefault("reasoning", "")
        result.setdefault("matching_factors", [])
        result.setdefault("contradicting_factors", [])
        result.setdefault("recommendation", "REVIEW")
        # Clamp confidence
        result["confidence_score"] = max(0.0, min(1.0, float(result["confidence_score"])))
        return result
    except Exception as e:
        result = _mock_reason(lost_attrs, found_attrs)
        result["error"] = str(e)
        return result


def _mock_reason(lost_attrs: dict, found_attrs: dict) -> dict:
    """Generate a mock reasoning result based on attribute comparison."""
    score = 0.0
    matching = []
    contradicting = []

    if lost_attrs.get("category") == found_attrs.get("category"):
        score += 0.35
        matching.append("Same item category")
    else:
        contradicting.append("Different item categories")

    if lost_attrs.get("color") and found_attrs.get("color"):
        if lost_attrs["color"].lower() == found_attrs["color"].lower():
            score += 0.25
            matching.append("Color match")

    if lost_attrs.get("brand", "unknown") != "unknown" and found_attrs.get("brand", "unknown") != "unknown":
        if lost_attrs["brand"].lower() == found_attrs["brand"].lower():
            score += 0.25
            matching.append("Brand match")

    score += 0.1  # Base proximity bonus
    score = min(score, 1.0)

    if score >= 0.85:
        rec = "CONFIRM"
    elif score >= 0.60:
        rec = "REVIEW"
    else:
        rec = "REJECT"

    return {
        "confidence_score": round(score, 2),
        "reasoning": f"Mock analysis: {len(matching)} matching factors found, {len(contradicting)} contradictions.",
        "matching_factors": matching,
        "contradicting_factors": contradicting,
        "recommendation": rec,
    }
