"""
RAG System Test Document Generator
====================================
Generates a PDF test document with embedded facts and corresponding test questions
to validate retrieval accuracy, citation quality, and RBAC enforcement.

Usage:
    uv run python scripts/generate_test_doc.py data/test_doc.pdf

The document is classified as "internal" — only member/admin/owner roles can see it.
Run with --classification confidential to generate a confidential-gated doc.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.generate_corpus import build_styles, write_pdf


def generate(classification: str = "internal") -> dict:
    return {
        "filename": f"rag_test_document.pdf",
        "title": "RAG System Test Document — Project Atlas Knowledge Base",
        "author": "RAGForge QA Team",
        "department": "Engineering",
        "classification": classification,
        "date": "2026-06-17",
        "sections": [
            {
                "heading": "1. Product Overview",
                "content": [
                    "Project Atlas is NovaTech's enterprise Retrieval-Augmented Generation platform "
                    "for knowledge management. It was announced on January 15, 2026 and entered "
                    "private beta on March 1, 2026. The platform processes over 2.4 million "
                    "document chunks across engineering, product, and confidential collections.",
                    "The founding team consists of Deepa Iyer (CTO), Nalini Bose (CPO), and "
                    "Arjun Mehta (VP Engineering). The company is headquartered in San Francisco, "
                    "CA with a secondary office in Austin, TX.",
                    {"table": (
                        ["Metric", "Value", "Target"],
                        [
                            ["Documents indexed", "14 200", "25 000 (Q4 2026)"],
                            ["Avg queries per day", "8 500", "15 000 (Q4 2026)"],
                            ["P95 /ask latency", "480 ms", "< 300 ms"],
                            ["RAGAS faithfulness", "0.89", "> 0.85"],
                            ["Uptime SLA", "99.9%", "99.95%"],
                        ],
                        [2.2*8, 1.8*8, 2*8]
                    )},
                ],
            },
            {
                "heading": "2. Feature X — Multi-Document Q&A",
                "content": [
                    "Feature X is Project Atlas's flagship capability for querying across "
                    "multiple documents simultaneously. It was originally scheduled to launch "
                    "in July 2026 but has been pushed to August 2026 due to GPU scaling "
                    "challenges under multi-document load. The feature supports up to 50 "
                    "documents per query and uses a parallel retrieval strategy.",
                    "The Feature X team is led by Nalini Bose. The budget for Feature X "
                    "development is $2.4 million, allocated as $1.2M for engineering, "
                    "$800K for infrastructure, and $400K for evaluation and QA.",
                    {"bullets": [
                        "Parallel retrieval splits queries across document subsets and merges results.",
                        "Cross-document citation deduplication removes overlapping source references.",
                        "Latency budget: 200 ms retrieval + 250 ms LLM generation = 450 ms target P95.",
                        "Supported document limit will increase to 200 documents in Q1 2027.",
                    ]},
                ],
            },
            {
                "heading": "3. Pricing Tiers",
                "content": [
                    "Project Atlas offers three pricing tiers. Starter at $49/month includes "
                    "1,000 queries and 500 documents. Growth at $299/month includes 10,000 "
                    "queries and 10,000 documents with RBAC support. Enterprise is custom "
                    "priced with unlimited queries and documents.",
                    "The FinCorp enterprise pilot signed in March 2026 is priced at $48,000/year "
                    "for 1.2 million queries per month. This represents a 15% discount off "
                    "standard enterprise pricing.",
                ],
            },
            {
                "heading": "4. Security & RBAC Model",
                "content": [
                    "Project Atlas enforces role-based access control at three classification "
                    "levels: public (visible to all org members), internal (visible to members, "
                    "admins, and owners), and confidential (visible only to admins and owners).",
                    "The RBAC model was hardened following the March 2026 security incident "
                    "where unauthorized read access was discovered. Post-incident remediation "
                    "included: mTLS enforcement on all inter-pod communication, Qdrant API key "
                    "rotation, Kubernetes NetworkPolicy restricting Qdrant port 6333 to the "
                    "Retriever service namespace, and mandatory security review gates for all "
                    "new features.",
                    {"bullets": [
                        "mTLS via cert-manager with 90-day certificate rotation.",
                        "Qdrant API key stored in AWS Secrets Manager; rotated every 30 days.",
                        "Audit logging enabled with 90-day retention in CloudWatch Logs.",
                        "All document chunks carry classification and allowed_roles in Qdrant payload.",
                    ]},
                ],
            },
            {
                "heading": "5. Observability & Monitoring",
                "content": [
                    "NovaTech uses Prometheus, Grafana, and CloudWatch for monitoring. "
                    "The /ask endpoint has an SLO of 99.9% availability with P95 latency "
                    "under 500 ms. Error rate SLO is under 0.5%.",
                    "OpenTelemetry SDK is integrated via middleware into every FastAPI service. "
                    "Traces are exported to AWS Managed Grafana Tempo. The Qdrant client was "
                    "instrumented with OpenTelemetry after the March 2026 incident.",
                ],
            },
            {
                "heading": "6. Qdrant Vector Store Configuration",
                "content": [
                    "Production Qdrant runs a 3-node cluster on AWS EKS using r6g.2xlarge "
                    "instances (64 GB RAM, 8 vCPU). Each node stores a shard replica with "
                    "all shards replicated twice for fault tolerance.",
                    "HNSW index parameters: m=16, ef_construct=200, ef=128. Collections use "
                    "BAAI/bge-base-en-v1.5 embeddings (768 dimensions) with cosine distance. "
                    "Hybrid retrieval combines dense + BM25 sparse vectors fused via RRF with k=60.",
                ],
            },
            {
                "heading": "7. Evaluation & RAGAS Scores",
                "content": [
                    "RAGAS evaluation runs weekly against a 200-question golden dataset. Current "
                    "scores as of June 2026: faithfulness 0.89, answer relevance 0.86, context "
                    "precision 0.82, context recall 0.79. The GA target for all metrics is > 0.85.",
                    "A drop of more than 0.05 in any metric over 7 days triggers a retrieval "
                    "review meeting. The last retrieval review was triggered on June 10, 2026 "
                    "due to a context recall dip from 0.79 to 0.73.",
                ],
            },
            {
                "heading": "8. Test Queries",
                "content": [
                    "The following questions can be asked against this document to validate "
                    "RAG system behavior. Each question targets specific facts above.",
                    {"bullets": [
                        "When was Project Atlas announced?",
                        "Who are the founding team members of Project Atlas?",
                        "How much is the Project Atlas Starter tier per month?",
                        "How many queries per month does the Growth tier include?",
                        "What is the FinCorp pilot priced at per year?",
                        "What are the three classification levels in Project Atlas RBAC?",
                        "What security measures were implemented after the March 2026 incident?",
                        "How many document chunks does Project Atlas process?",
                        "What is the current RAGAS faithfulness score?",
                        "What is Feature X and when is it launching?",
                        "What is the budget for Feature X development?",
                        "What HNSW index parameters does Qdrant use in production?",
                        "What embedding model and dimensions does Project Atlas use?",
                        "What SLO does the /ask endpoint have for availability?",
                        "What triggers a retrieval review meeting?",
                    ]},
                ],
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate RAG system test document")
    parser.add_argument("output", nargs="?", default="data/test_doc.pdf",
                        help="Output PDF path (default: data/test_doc.pdf)")
    parser.add_argument("--classification", choices=["public", "internal", "confidential"],
                        default="internal",
                        help="Document classification level (default: internal)")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    doc_data = generate(args.classification)
    write_pdf(args.output, {k: doc_data[k] for k in ("title", "author", "department", "classification", "date")}, doc_data["sections"])
    print(f"\nGenerated test document: {args.output}")
    print(f"Classification: {args.classification}")
    print(f"Upload it, then ask the 15 questions in section 8 to validate RAG behavior.\n")


if __name__ == "__main__":
    main()
