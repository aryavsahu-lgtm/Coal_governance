import re
from typing import List, Dict, Any
from app.rag.knowledge_base import STATUTORY_KNOWLEDGE_CORPUS


def retrieve_statutory_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant regulatory sections based on term overlap
    and statutory regulation identifiers.
    """
    cleaned_query = query.lower()
    query_tokens = set(re.findall(r"\b\w{3,}\b", cleaned_query))

    scored_results = []

    for item in STATUTORY_KNOWLEDGE_CORPUS:
        score = 0.0
        doc_text = (item["title"] + " " + item["content"] + " " + item["regulation"] + " " + item["category"]).lower()
        doc_tokens = set(re.findall(r"\b\w{3,}\b", doc_text))

        # Direct token match
        overlap = query_tokens.intersection(doc_tokens)
        score += len(overlap) * 2.5

        # Bonus for specific keywords
        if "helmet" in cleaned_query or "ppe" in cleaned_query:
            if "191" in item["regulation"]:
                score += 10.0
        if "accident" in cleaned_query or "injury" in cleaned_query or "death" in cleaned_query:
            if "23" in item["regulation"]:
                score += 10.0
        if "dust" in cleaned_query or "water" in cleaned_query or "spray" in cleaned_query:
            if "104" in item["regulation"]:
                score += 10.0
        if "fire" in cleaned_query or "smoke" in cleaned_query or "combustion" in cleaned_query:
            if "110" in item["regulation"]:
                score += 10.0
        if "machinery" in cleaned_query or "dumper" in cleaned_query or "truck" in cleaned_query or "road" in cleaned_query:
            if "228" in item["regulation"]:
                score += 10.0
        if "slope" in cleaned_query or "bench" in cleaned_query or "highwall" in cleaned_query:
            if "03/2021" in item["regulation"]:
                score += 10.0

        if score > 0:
            scored_results.append({
                "item": item,
                "score": score
            })

    scored_results.sort(key=lambda x: x["score"], reverse=True)
    top_matches = [s["item"] for s in scored_results[:top_k]]

    # If no match found, return the top default PPE and Accident regulations
    if not top_matches:
        top_matches = STATUTORY_KNOWLEDGE_CORPUS[:2]

    return top_matches
