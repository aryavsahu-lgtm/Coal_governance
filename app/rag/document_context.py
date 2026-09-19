import re
import logging
from typing import Dict, Any, List, Optional
from app.database.mongo import mongo

logger = logging.getLogger("coal_governance.rag.documents")

DOC_REGEX_TRIGGERS = re.compile(
    r"\b(contract|contracts|agreement|agreements|contract\s*details|contract\s*terms|scope\s*of\s*work|"
    r"penalty|penalties|sop|sops|procedure|procedures|safety\s*rules|emergency\s*rules|evacuation|"
    r"muster\s*station|speed\s*limit|berm|slope\s*angle|uploaded\s*doc\w*)\b",
    re.IGNORECASE
)


def is_document_query(query: str) -> bool:
    """
    Detects if the query relates to uploaded statutory documents,
    contractor agreements, or mine SOPs.
    """
    ql = query.lower()
    # If the user is asking about contractor risk rankings / operational contractor metrics
    if ("contractor" in ql or "contractors" in ql) and ("risk" in ql or "who" in ql or "highest" in ql or "worst" in ql) and not any(k in ql for k in ["detail", "agreement", "term", "penalty", "clause", "upload", "doc"]):
        return False

    return bool(DOC_REGEX_TRIGGERS.search(ql))


def retrieve_document_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Searches uploaded documents, contractor agreements, and SOPs in mongo.documents
    using lexical token overlap and keyword boosting.
    """
    try:
        all_docs = list(mongo.documents.find())
    except Exception as e:
        logger.error(f"[DocumentRAG] Failed to query mongo.documents: {e}")
        all_docs = []

    if not all_docs:
        return []

    ql = query.lower()
    query_tokens = set(re.findall(r"\b\w{3,}\b", ql))

    scored_docs = []

    for d in all_docs:
        score = 0.0
        fname = str(d.get("original_filename", "")).lower()
        doc_type = str(d.get("document_type", "")).lower()
        doc_num = str(d.get("document_number", "")).lower()
        extracted_text = str(d.get("extracted_text", "")).lower()

        combined_text = f"{fname} {doc_type} {doc_num} {extracted_text}"
        doc_tokens = set(re.findall(r"\b\w{3,}\b", combined_text))

        # Direct token overlap
        overlap = query_tokens.intersection(doc_tokens)
        score += len(overlap) * 2.0

        # Targeted Boosts
        if ("contract" in ql or "agreement" in ql or "penalty" in ql or "earthmovers" in ql or "vendor" in ql):
            if "contract" in doc_type or "contract" in fname or "agreement" in doc_type:
                score += 15.0
            if "abc" in ql and "abc" in combined_text:
                score += 20.0

        if ("sop" in ql or "procedure" in ql or "speed" in ql or "berm" in ql or "slope" in ql):
            if "sop" in doc_type or "sop" in fname or "procedure" in doc_type:
                score += 15.0
            if "sop-04" in ql or "sop 04" in ql or "sop-rjm" in ql:
                if "04" in fname or "04" in doc_num or "sop-rjm" in combined_text:
                    score += 25.0

        if ("safety rule" in ql or "emergency" in ql or "evacuation" in ql):
            if "safety_rules" in doc_type or "rule" in fname or "emergency" in combined_text:
                score += 15.0

        if score > 0:
            scored_docs.append({
                "doc": d,
                "score": score
            })

    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return [s["doc"] for s in scored_docs[:top_k]]


def synthesize_document_response(query: str, matched_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Synthesizes a precise factual answer extracted from uploaded documents,
    contractor agreements, or SOPs with source citations.
    """
    if not matched_docs:
        return {
            "response": (
                "No matching uploaded contracts, SOPs, or safety documents found in the database. "
                "Please upload the required document in the **Document Vault & OCR** portal to enable AI querying."
            ),
            "citations": []
        }

    primary = matched_docs[0]
    fname = primary.get("original_filename", "Document")
    doc_num = primary.get("document_number", "N/A")
    doc_type = primary.get("document_type", "GENERAL").replace("_", " ").title()
    text = primary.get("extracted_text", "")
    ql = query.lower()

    citations = [{
        "doc_id": str(primary.get("_id", "DOC-OCR")),
        "regulation": f"Uploaded Document: {fname} ({doc_num})",
        "title": f"OCR Extracted Document - {doc_type}",
        "authority": primary.get("authority", "DGMS / Central Coal Governance Repository"),
        "category": "Uploaded Documents & Contracts OCR"
    }]

    # 1. Contract inquiry synthesis
    if any(k in ql for k in ["contract", "agreement", "earthmovers", "vendor", "penalty", "insurance"]):
        response = (
            f"### 📑 Contractor Agreement Details: **{fname}**\n\n"
            f"- **Contract Reference:** `{doc_num}`\n"
            f"- **Document Classification:** {doc_type}\n"
            f"- **Status / OCR Validity:** {primary.get('status', 'ACTIVE')}\n\n"
            f"#### 🔍 Key Terms & Contractual Details Extracted via OCR:\n"
        )

        # Extract highlighted clauses
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            if any(term in line.lower() for term in ["contractor:", "value:", "period:", "workers:", "scope of work:", "clause", "penalty", "insurance"]):
                response += f"- **{line}**\n" if ":" in line else f"- {line}\n"

        response += (
            f"\n> **Statutory Compliance Mandate:**\n"
            f"> Under DGMS regulations and Coal India guidelines, the contractor is bound by these statutory safety clauses. "
            f"Failure to adhere to PPE or machine alarm rules triggers contractual penalties and immediate escalation."
        )

        return {
            "response": response,
            "citations": citations
        }

    # 2. SOP & Safety Rules inquiry synthesis
    if any(k in ql for k in ["sop", "procedure", "speed", "berm", "slope", "evacuation", "emergency", "rule"]):
        response = (
            f"### 📘 Mine Standard Operating Procedure (SOP): **{fname}**\n\n"
            f"- **SOP Reference Number:** `{doc_num}`\n"
            f"- **Classification:** {doc_type}\n"
            f"- **Issuing Authority:** {primary.get('authority', 'DGMS / CIL Safety Directorate')}\n\n"
            f"#### ⚙️ Mandated Operating Parameters & Safety Rules:\n"
        )

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            if any(term in line.lower() for term in ["speed limit", "berm", "slope", "dust", "evacuation", "parameter", "siren", "rule", "procedure"]):
                response += f"- {line}\n"

        response += (
            f"\n> **On-Site Operational Requirement:**\n"
            f"> All shift supervisors, dumper operators, and HEMM contractors must follow these exact parameters. "
            f"Periodic audits by the Safety Officer verify physical adherence to these SOP rules."
        )

        return {
            "response": response,
            "citations": citations
        }

    # 3. General Document Content Fallback
    preview_text = text[:800] + ("..." if len(text) > 800 else "")
    response = (
        f"### 📄 Document Content: **{fname}** ({doc_num})\n\n"
        f"- **Type:** {doc_type} | **Authority:** {primary.get('authority', 'DGMS')}\n"
        f"- **Validity / Expiry:** {primary.get('expiry_date', 'Not specified')}\n\n"
        f"**Extracted OCR Content:**\n\n"
        f"```text\n{preview_text}\n```\n"
    )

    return {
        "response": response,
        "citations": citations
    }
