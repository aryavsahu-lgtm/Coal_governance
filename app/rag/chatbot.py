import os
import logging
from typing import Dict, Any, List
from app.rag.retriever import retrieve_statutory_context
from app.rag.operational_context import is_operational_query, generate_operational_synthesis
from app.rag.document_context import is_document_query, retrieve_document_context, synthesize_document_response

logger = logging.getLogger("coal_governance.rag")

STATUTORY_KEYWORDS = [
    "cmr", "regulation", "reg", "act", "section", "dgms", "circular", "rule",
    "law", "mandate", "statutory", "permissible", "penalty", "requirement",
    "standard", "legal", "clause", "form iv", "smp", "safety management plan"
]


def has_statutory_intent(query: str) -> bool:
    """Checks if the query contains statutory, legal, or regulatory keywords."""
    ql = query.lower()
    return any(k in ql for k in STATUTORY_KEYWORDS)


def generate_rag_response(user_query: str) -> Dict[str, Any]:
    """
    Unified Regulatory, Operational & Document AI Assistant.
    Seamlessly answers queries on:
    1) Uploaded Contractor Agreements & Mines SOPs (via OCR text extraction)
    2) Live Operational Database Metrics (mine violation counts, rankings, contractor risks, CAPAs)
    3) DGMS Statutory Regulations (CMR 2017, Mines Act 1952, DGMS Circulars)
    4) Multi-source hybrid cross-queries combining contracts, live metrics, and legal mandates.
    """
    if not user_query or not user_query.strip():
        return {
            "query": user_query,
            "response": "Please specify your query regarding contractor agreements, mine SOPs, live violation analytics, or DGMS safety regulations.",
            "citations": []
        }

    user_query = user_query.strip()
    is_doc = is_document_query(user_query)
    is_op = is_operational_query(user_query)
    is_stat = has_statutory_intent(user_query)

    # 1. Document Context Retrieval (SOPs, Contracts, Safety Rules)
    doc_result = None
    if is_doc:
        matched_docs = retrieve_document_context(user_query)
        if matched_docs:
            doc_result = synthesize_document_response(user_query, matched_docs)

    # 2. Operational Context Retrieval (Mine Violations, Contractors, CAPAs)
    # If it's purely a document query without mine comparison, op_result can be skipped
    op_result = None
    if is_op and not (doc_result and not any(k in user_query.lower() for k in ["which mine", "rank", "compare", "more violation", "most violation"])):
        op_result = generate_operational_synthesis(user_query)

    # 3. Statutory Regulatory Retrieval (CMR 2017 & Mines Act)
    retrieved_docs = []
    if is_stat or (not is_op and not is_doc and not doc_result):
        retrieved_docs = retrieve_statutory_context(user_query, top_k=2)

    # Compile all citations
    citations = []
    if doc_result and "citations" in doc_result:
        citations.extend(doc_result["citations"])
    if op_result and "citations" in op_result:
        citations.extend(op_result["citations"])
    for doc in retrieved_docs:
        citations.append({
            "doc_id": doc["doc_id"],
            "regulation": doc["regulation"],
            "title": doc["title"],
            "authority": doc["authority"],
            "category": doc["category"]
        })

    # Check for external LLM API key (Gemini)
    gemini_key = os.getenv("GEMINI_API_KEY")

    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            context_blocks = []
            if doc_result:
                context_blocks.append(f"### UPLOADED CONTRACTOR AGREEMENTS & MINES SOPS (OCR EXTRACTED):\n{doc_result['response']}")
            if op_result:
                context_blocks.append(f"### LIVE OPERATIONAL DATABASE METRICS:\n{op_result['response']}")
            if retrieved_docs:
                stat_text = "\n\n".join([f"[{d['regulation']} - {d['title']}]: {d['content']}" for d in retrieved_docs])
                context_blocks.append(f"### STATUTORY CMR 2017 & MINES ACT 1952 REGULATIONS:\n{stat_text}")

            full_context = "\n\n".join(context_blocks)
            prompt = (
                f"You are an expert DGMS Compliance Officer and Mining Legal Consultant.\n"
                f"Answer the user query strictly based on the provided document OCR text, operational metrics, and statutory context.\n"
                f"Do NOT hallucinate contractual figures, violation counts, or statutory rules.\n"
                f"When discussing contract details, quote the exact contractor name, contract value, penalty clauses, and validity dates.\n"
                f"When discussing SOPs, cite the exact operating parameters (speed limits, berm heights, slope angles).\n"
                f"When discussing mine rankings, cite the exact figures from the operational database.\n"
                f"Cite the relevant regulation name and section when discussing statutory safety requirements.\n\n"
                f"Context:\n{full_context}\n\n"
                f"User Question: {user_query}"
            )
            resp = model.generate_content(prompt)
            answer_text = resp.text
            return {
                "query": user_query,
                "response": answer_text,
                "citations": citations,
                "engine": "Gemini-1.5-Flash + Document OCR & Statutory RAG"
            }
        except Exception as ge:
            logger.warning(f"External Gemini API call failed ({ge}). Using deterministic synthesis.")

    # High-precision Zero-Hallucination Deterministic Engine
    response_parts = []

    # 1. Document / Contract OCR response
    if doc_result:
        response_parts.append(doc_result["response"])

    # 2. Operational data response
    if op_result:
        if response_parts:
            response_parts.append(f"\n\n---\n{op_result['response']}")
        else:
            response_parts.append(op_result["response"])

    # 3. Statutory legal response
    if retrieved_docs and (is_stat or (not doc_result and not op_result)):
        primary_doc = retrieved_docs[0]
        sec_doc = retrieved_docs[1] if len(retrieved_docs) > 1 else None

        if response_parts:
            response_parts.append(
                f"\n\n---\n### 📜 Related Statutory DGMS Regulations\n"
                f"Under Indian statutory coal mining laws, specifically **{primary_doc['regulation']}** ({primary_doc['title']}), the mandated requirement is:\n\n"
                f"> \"{primary_doc['content']}\"\n\n"
            )
        else:
            response_parts.append(
                f"Under Indian statutory coal mining laws, specifically **{primary_doc['regulation']}** ({primary_doc['title']}), the mandated requirement is as follows:\n\n"
                f"> \"{primary_doc['content']}\"\n\n"
            )

        if sec_doc and sec_doc["doc_id"] != primary_doc["doc_id"]:
            response_parts.append(
                f"Furthermore, statutory guidance under **{sec_doc['regulation']}** provides:\n"
                f"> \"{sec_doc['content']}\"\n\n"
            )

        response_parts.append(
            f"**Statutory Authority:** {primary_doc['authority']}.\n"
            f"**Compliance Action Required:** Immediate logging in the statutory register, adherence to safety SOPs, and inspection verification."
        )

    engine_name = "DGMS Unified OCR & Statutory Knowledge Engine"
    if doc_result:
        engine_name = "DGMS Document OCR & Contract Intelligence Engine"
    elif op_result:
        engine_name = "DGMS Hybrid Operational & Statutory Engine"

    return {
        "query": user_query,
        "response": "".join(response_parts),
        "citations": citations,
        "engine": engine_name
    }
