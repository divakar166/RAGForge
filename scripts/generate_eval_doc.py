"""
RAG System E2E Evaluation Document Generator
=============================================
Generates a comprehensive PDF with facts drawn from ALL 30 corpus documents
(Engineering, Product, and Confidential), followed by 40+ test questions
covering fact retrieval, cross-document conflicts, multi-hop reasoning,
classification gating, and comparative analysis.

Usage:
    uv run python scripts/generate_eval_doc.py data/eval_guide.pdf
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.generate_corpus import build_styles, write_pdf


def generate() -> dict:
    return {
        "filename": "rag_evaluation_guide.pdf",
        "title": "RAGForge E2E Evaluation Guide — 30-Document Validation Suite",
        "author": "RAGForge QA Team",
        "department": "Cross-Functional",
        "classification": "internal",
        "date": "2026-06-18",
        "sections": [
            # ─────────────────────────────────────────────────────────────────
            # SECTION 1 — Engineering
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "1. Engineering Domain — Architecture & Infrastructure",
                "content": [
                    "Project Atlas is NovaTech's enterprise RAG platform, announced January 15, 2026, "
                    "with private beta beginning March 1, 2026. The founding engineering team includes "
                    "Deepa Iyer (CTO) and Arjun Mehta (VP Engineering).",
                    "The platform uses FastAPI with a domain-driven project layout split into "
                    "routers, services, repositories, schemas, and core layers. Middleware includes "
                    "CorrelationID, Auth, RateLimit, and Compression. Performance benchmarks show "
                    "/ask (RAG) at P50 = 210 ms, sustaining 340 RPS on an AWS m6i.2xlarge instance.",
                    "Production Qdrant v1.10 runs on a 3-node r6g.2xlarge EKS cluster in AWS, "
                    "serving approximately 2.4 million document chunks across four collections: "
                    "eng_docs, prod_docs, conf_docs, and stackoverflow. Each node stores 64 GB RAM "
                    "and 8 vCPU. HNSW parameters: m = 16, ef_construct = 200, ef = 128. Embeddings "
                    "use BAAI/bge-base-en-v1.5 (768 dimensions) with cosine distance. Hybrid "
                    "retrieval combines dense top-k = 40 with BM25 sparse top-k = 40, fused via "
                    "RRF with k = 60. A CrossEncoder reranker runs on a g4dn.xlarge instance.",
                    "The retrieval pipeline: RBAC validation → embed → hybrid search on permitted "
                    "collections → RRF fusion → rerank top 20 → pass top 5 to Claude Sonnet 4 "
                    "with citation prompt → stream response.",
                    "RAGAS evaluation runs weekly against a 200-question golden dataset. Current "
                    "scores (June 2026): faithfulness 0.89, answer relevance 0.86, context "
                    "precision 0.82, context recall 0.79. GA targets require all metrics > 0.85. "
                    "A drop exceeding 0.05 in any metric over 7 days triggers a retrieval review "
                    "meeting; the last such meeting was June 10, 2026 due to a context recall dip "
                    "from 0.79 to 0.73.",
                    "Redis caching uses a 3-node ElastiCache r7g.large cluster with 3 shards "
                    "totalling 18 GB. A semantic cache layer in Project Atlas v2.1 uses Qdrant "
                    "nearest-neighbour lookup (cosine threshold 0.96), returning cached responses "
                    "in under 15 ms versus a 210 ms median pipeline time. Auth token caching "
                    "reduced PostgreSQL read load by 42%.",
                    "Celery job queues: ingest concurrency = 4, embed = 2, rerank = 8, notify = 16, "
                    "dlq = 1. Tasks use exponential backoff with max_retries = 5 and a dead letter "
                    "queue. Project Phoenix (Q3 2026) will consolidate four cron scripts into "
                    "Celery Beat, removing ~1 200 lines of scheduler code.",
                    {"table": (
                        ["Metric", "Current", "Target"],
                        [
                            ["API Availability SLO", "99.9%", "99.95%"],
                            ["/ask P95 latency", "480 ms", "< 300 ms"],
                            ["Qdrant Search P99", "< 200 ms", "< 150 ms"],
                            ["Error Rate SLO", "< 0.5%", "< 0.3%"],
                            ["Query volume (Q1 2026)", "4.2M/month", "—"],
                        ],
                        [2.4*8, 1.8*8, 1.6*8],
                    )},
                    "CI/CD: GitHub Actions with 8 stages — Ruff/Black lint (zero violations), "
                    "pytest ≥ 85% coverage, Trivy/Bandit (no HIGH/CRIT CVEs), Pact contract tests, "
                    "Docker build with Cosign signature, k6 performance gate (P95 < 500 ms at "
                    "100 RPS), ArgoCD canary deploy (5% → 25% → 100%). Feature flags via "
                    "LaunchDarkly decouple deploy from release.",
                    "Vector search lesson learned: BAAI/bge-base-en-v1.5 chosen after evaluating "
                    "8 models on 3 200 query–document pairs, achieving NDCG@10 = 0.74. Uses "
                    "recursive character chunking (chunk_size = 512, overlap = 64) with sentence "
                    "boundary detection.",
                    "API versioning follows URI-path convention (/v1/, /v2/, /v3/) with RFC 8594 "
                    "Deprecation and Sunset headers (180-day timeline). v1 GA since 2024-09-01 "
                    "with support until 2027-09-01. v2 introduced async streaming and pagination "
                    "cursors in January 2026. v3 targets GA in Q4 2026.",
                    "Three-pillar observability: Prometheus/Grafana metrics, Tempo/OpenTelemetry "
                    "traces, CloudWatch JSON logs. Traces sample at 100% for errors, 5% for "
                    "successes. After the March 2026 incident, all Qdrant calls emit OTel spans. "
                    "Kubernetes: two EKS clusters (us-east-1 primary, eu-west-1 DR). CPU-bound "
                    "services use HPA at 65% CPU. Celery workers use KEDA with Redis queue-length "
                    "trigger (1 worker per 50 pending, min = 2, max = 20). Policies enforce "
                    "non-root pods, read-only root filesystems, OPA Gatekeeper, Cosign image "
                    "verification, and Trivy scanning — HIGH CVEs block merges.",
                ],
            },
            # ─────────────────────────────────────────────────────────────────
            # SECTION 2 — Product
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "2. Product Domain — Roadmap, Pricing & Market",
                "content": [
                    "Q3 2026 roadmap themes: Project Atlas GA, Enterprise Analytics Dashboard, "
                    "Project Phoenix self-serve onboarding, and SOC 2 Type II compliance. "
                    "Feature X (multi-document Q&A) is the flagship capability; it supports up "
                    "to 50 documents per query with a parallel retrieval strategy that splits "
                    "documents into subsets and merges results. The Feature X team is led by "
                    "Nalini Bose (CPO). Its budget is $2.4 million: $1.2M engineering, $800K "
                    "infrastructure, $400K evaluation and QA.",
                    "The Feature X launch date appears differently across documents. The Q3 "
                    "roadmap schedules it for July 2026 (marked \"At Risk\" due to latency > 500 ms "
                    "under multi-document load), while the GA launch plan states it will launch "
                    "alongside Project Atlas GA in August 2026, pending resolution of the P95 "
                    "latency issue.",
                    "Project Phoenix self-serve onboarding targets September 2026. EU Data "
                    "Residency targets August 2026.",
                    "Pricing (2026): Starter $49/month (1 000 queries, 500 documents), Growth "
                    "$299/month (10 000 queries, 10 000 documents, RBAC), Enterprise (custom). "
                    "Shifted from per-seat to usage-based pricing for Growth after 14 customer "
                    "interviews. Targets $0.03/query at Growth volume (58% contribution margin). "
                    "Enterprise pilot with FinCorp signed March 2026 at $48 000/year for "
                    "1.2 million queries/month.",
                    "Customer feedback (Q1 2026): 847 NPS responses, 34 interviews, 1 200 in-app "
                    "submissions. NPS improved from 31 to 44 year-over-year. Top feature requests: "
                    "multi-document Q&A (68% of Growth customers), Slack integration (54% of "
                    "Enterprise prospects), RBAC for shared workspaces (47%). Project Atlas beta "
                    "users (34 accounts) report 91% satisfaction with answer quality. TechRetail "
                    "reported 3× reduction in support escalations.",
                    "RICE scores for Q3 2026: Feature X = 84, Analytics Dashboard = 100, "
                    "Slack Integration = 71, EU Residency = 68, Custom Embeddings = 17. "
                    "Scores > 50 enter the roadmap automatically.",
                    "Q1 2026 analytics: MAU grew 34% to 12 400, query volume 4.2M/month (up 50% "
                    "QoQ). Day-30 retention improved from 38% to 51% after an onboarding redesign "
                    "in February 2026. After migrating from keyword search to Qdrant hybrid "
                    "retrieval in January 2026, \"Answer Not Found\" rate dropped from 18% to 6%. "
                    "Users receiving cited answers have 2.4× higher Day-30 retention.",
                    "Market research: TAM for AI-powered enterprise search estimated at $4.2B "
                    "in 2026, growing at 38% CAGR. Top buying criteria: data security (84%), "
                    "answer accuracy (79%), tool integrations (71%). 67% of respondents require "
                    "SOC 2 Type II before procurement (up from 48% in 2025).",
                    "Customer segmentation (1 840 paying accounts): Developer Hobbyists 24% "
                    "(4% ARR), Technical SMBs 38% (22% ARR), Mid-Market Operations 28% "
                    "(33% ARR), Enterprise 10% (61% ARR). Enterprise ARR averages $15 000+ "
                    "per account. Mid-Market Atlas adopters show 4.2× higher expansion rate "
                    "($8 200 vs $1 950 NRR).",
                    "Monthly logo churn was 2.1% in Q1 2026, exceeding the 1.5% target. "
                    "Drivers: poor onboarding completion (44%), low 30-day query volume (31%), "
                    "lack of RBAC configuration (18%). Project Phoenix wizard shows 87% "
                    "completion in internal testing vs 41% for the current flow.",
                    "Competitive analysis: NovaTech leads on retrieval accuracy (Qdrant hybrid "
                    "search NDCG@10 = 0.74 vs Glean's 0.69) and RBAC granularity. Glean leads "
                    "on integration breadth. SearchAI (stealth startup, ex-Google Brain team, "
                    "8 employees) is a potential acqui-hire target. Emerging threats include "
                    "Glean v3 (rumoured vector DB integration) and a potential OpenAI enterprise "
                    "search product in H2 2026.",
                ],
            },
            # ─────────────────────────────────────────────────────────────────
            # SECTION 3 — Confidential
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "3. Confidential Domain — Finance, Security & Strategy",
                "content": [
                    "Executive compensation FY 2026 (approved 2026-01-10): CEO base $420 000 "
                    "with 80% target bonus ($336K), $1.8M RSU grant, $600K LTIP target. "
                    "CTO $360K base, CPO $320K, CFO $310K, VP Eng $290K, VP Sales $260K. "
                    "LTIP milestones tied to ARR > $12M, Atlas NPS > 45, and Series B close. "
                    "RSUs vest over 4 years with 1-year cliff.",
                    "Salary bands (SF Bay Area, Radford P50 for L1-3, P65 for L4-5): "
                    "Engineering — E1 Junior $105–130K, E2 Software $135–168K, E3 Senior "
                    "$168–215K, E4 Staff $215–275K, E5 Principal $265–345K. "
                    "Product — P1 Associate PM $110–135K, P4 Group PM/Director $220–290K. "
                    "84 employees eligible for equity refreshes with $4.2M total RSU budget.",
                    "Acquisition discussions with SearchAI (codename: Project Nightingale). "
                    "Valued at $18–22M. Deal structure: $8–10M cash, $10–12M RSU, $2M retention "
                    "pool. LOI target: May 2026. Due diligence: 6–8 weeks. Close: Q3 2026. "
                    "Risk: competing offer from Glean.",
                    "March 2026 security incident: on 2026-03-14, a misconfigured network policy "
                    "allowed a compromised staging pod to reach the production Qdrant API (auth "
                    "disabled for \"testing purposes\"). ~4 200 document chunks read by attacker "
                    "before containment at 03:47 UTC. No user PII accessed. Root cause: Kubernetes "
                    "NetworkPolicy update on 2026-03-12 removed namespace isolation; exploited "
                    "via CVE-2024-8819. Incident cost estimated at $340 000; $5M AIG cyber "
                    "insurance claim filed.",
                    "Internal audit Q1 2026: 8 findings (2 High, 4 Medium, 2 Low). March incident "
                    "contributed 3: A01 — Qdrant API auth disabled, A02 — staging-to-prod "
                    "network path unrestricted, A03 — missing OTel instrumentation on Qdrant "
                    "client. Other findings: expired SearchAI vendor NDA, $14 200 in off-cycle "
                    "expense claims lacking dual approval, overdue encryption key rotation.",
                    "Budget forecast FY 2027 (draft): base scenario projects $22M ARR by "
                    "December 2027, requiring $14M Series B in Q4 2026 to grow headcount "
                    "from 62 to 102. Project Atlas allocated $8.4M (34% of total opex). "
                    "The draft incorrectly states the FY 2026 Atlas budget as $2.4M — the "
                    "correct Board-approved figure is $2.8M.",
                    "Board meeting 2026-03-30 (5 board members). Key resolutions: "
                    "(1) Approved Project Atlas budget $2.8M for FY 2026 (amended from $2.4M "
                    "following the March incident — resolution 2026-Q1-01, vote 5-0). "
                    "(2) Authorised preliminary due diligence on Project Nightingale. "
                    "(3) Approved Series B mandate to Goldman Sachs ($14–20M, targeting "
                    "Q4 2026 close). ARR reached $9.2M (up 28% QoQ), 34 enterprise Atlas "
                    "beta users, NPS 44.",
                    "Infrastructure risk assessment Q2 2026: 6 identified risks. "
                    "R01 — single-region EKS with DR at only 60% parity (High). "
                    "R02 — Qdrant at 78% capacity, projected to hit 90% by July 2026 "
                    "causing ~40% HNSW performance degradation (High). "
                    "R03 — 100% LLM vendor concentration on Anthropic, no fallback (Medium). "
                    "Qdrant 3-node expansion budgeted at $4 200/month, target 2026-06-15. "
                    "Key-person dependency on Deepa Iyer noted.",
                    "Compliance investigation into vendor expenses: two POs totalling $14 200 "
                    "lacked dual approval — $8 400 W&B license (violation of Procurement "
                    "Policy section 4.2) and $5 800 Lambda Labs GPU credits on personal card. "
                    "Both purchases were legitimate. Retroactive approvals obtained. Finance "
                    "implementing automated procurement gate in Ramp for all transactions > $3 000.",
                    "Strategic partnership negotiations: FinCorp (12 000 employees, financial "
                    "services, proposed $480K/year ARR for 3 years, deploying across 2.4M "
                    "documents and 18K Confluence pages) and RetailMax (4 500 employees, "
                    "e-commerce, proposed $180K/year ARR, 400K queries/month for 800 support "
                    "agents). Combined ARR: $2.1M. Both deals gated on SOC 2 Type II and EU "
                    "data residency. Risk: Atlas GA slip beyond August may push RetailMax to Q4.",
                ],
            },
            # ─────────────────────────────────────────────────────────────────
            # SECTION 4 — Cross-Document Conflicts & Contradictions
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "4. Intentional Cross-Document Conflicts",
                "content": [
                    "The corpus contains deliberate contradictions to test retrieval accuracy "
                    "and the RAG system's ability to surface authoritative sources:",
                    {"bullets": [
                        "Feature X launch date: prod_01_roadmap (internal) says July 2026; "
                        "prod_08_launch_plan (internal) says August 2026 alongside GA. "
                        "The launch plan is the more authoritative GTM document.",
                        "Project Atlas FY 2026 budget: conf_06_budget (confidential, draft) "
                        "says $2.4M; conf_07_board_minutes (confidential, approved) says $2.8M. "
                        "The Board minutes are the authoritative source — the budget was amended "
                        "from $2.4M to $2.8M after the March incident.",
                        "SearchAI's status: prod_10_competitive (internal) describes it as a "
                        "competitor; conf_03_acquisition (confidential) reveals acquisition "
                        "discussions codenamed Project Nightingale. Only confidential-cleared "
                        "users should see the acquisition context.",
                        "Qdrant cluster size mentioned in eng_02_qdrant_deployment (internal) "
                        "as 3-node r6g.2xlarge; confirmed in conf_08_infra_risk (confidential) "
                        "which adds that expansion is budgeted at $4 200/month.",
                    ]},
                ],
            },
            # ─────────────────────────────────────────────────────────────────
            # SECTION 5 — Classification Gating
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "5. Classification Gating Test Cases",
                "content": [
                    "Documents are classified into three tiers with corresponding RBAC rules:",
                    {"table": (
                        ["Tier", "Example Facts", "Visible To"],
                        [
                            ["Public",
                             "FastAPI architecture, API versioning policy, CI/CD standards, pricing tiers",
                             "All org roles (viewer, member, admin, owner)"],
                            ["Internal",
                             "Qdrant deployment, Redis caching, Celery jobs, roadmap, customer feedback, "
                             "competitive analysis, RAGAS scores, Feature X details",
                             "Members, admins, and owners"],
                            ["Confidential",
                             "Executive compensation, salary bands, acquisition talks, security incident "
                             "details, audit findings, budget forecasts, board minutes, partnership "
                             "negotiations",
                             "Admins and owners only"],
                        ],
                        [2.0*8, 3.4*8, 2.6*8],
                    )},
                    "Viewer role users should ONLY retrieve public documents. "
                    "Member role users should retrieve public + internal documents. "
                    "Admin and owner roles should retrieve all classifications. "
                    "Questions about confidential facts (e.g., CEO salary, Series B details, "
                    "incident costs) should return empty or \"I cannot find\" for viewer/member queries.",
                ],
            },
            # ─────────────────────────────────────────────────────────────────
            # SECTION 6 — Test Questions
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "6. E2E RAG Validation Questions",
                "content": [
                    "Ask each question against the uploaded 30-document corpus. Use the table at the "
                    "end of this document to record expected vs actual answers, citation sources, and "
                    "whether the answer was correct.",
                    "",
                    "<b>Category A — Simple Fact Retrieval (Engineering)</b>",
                    {"bullets": [
                        "When was Project Atlas announced, and when did private beta begin?",
                        "What FastAPI middleware stack does NovaTech use?",
                        "How many document chunks does the production Qdrant cluster serve, and across how many collections?",
                        "What are the HNSW index parameters (m, ef_construct, ef) used in Qdrant?",
                        "What embedding model and dimensions does Project Atlas use?",
                        "How does hybrid retrieval work in the Project Atlas pipeline?",
                        "What are the four RAGAS metrics and their current June 2026 scores?",
                        "What event triggers a retrieval review meeting, and when was the last one?",
                        "How many shards and what instance type does the Redis cache cluster use?",
                        "What is the concurrency setting for Celery's ingest queue and rerank queue?",
                        "What performance benchmark does the /ask endpoint achieve (P50 latency, RPS)?",
                        "What are the two EKS cluster regions and the DR parity percentage?",
                        "What is the API versioning policy (URL scheme, deprecation timeline)?",
                        "What CI/CD tool and deploy strategy does NovaTech use?",
                        "What NDCG@10 score did the chosen embedding model achieve?",
                    ]},
                    "",
                    "<b>Category B — Simple Fact Retrieval (Product)</b>",
                    {"bullets": [
                        "What are the Q3 2026 roadmap themes?",
                        "How much does the Growth pricing tier cost, and how many queries does it include?",
                        "What was the NPS score in Q1 2026, and how did it change year-over-year?",
                        "What percentage of Growth customers requested multi-document Q&A?",
                        "What was the month-over-month query volume growth in Q1 2026?",
                        "What was the Day-30 retention rate before and after the onboarding redesign?",
                        "How much did the \"Answer Not Found\" rate drop after the hybrid retrieval migration?",
                        "What is the estimated TAM for AI-powered enterprise search in 2026?",
                        "What percentage of enterprise accounts require SOC 2 Type II?",
                        "What was the Q1 2026 monthly logo churn rate and the target?",
                    ]},
                    "",
                    "<b>Category C — Simple Fact Retrieval (Confidential)</b>",
                    {"bullets": [
                        "What is the CEO's base salary and target bonus percentage?",
                        "How many employees are eligible for equity refreshes and what is the total RSU budget?",
                        "What is the codename for the SearchAI acquisition discussions?",
                        "When did the March 2026 security incident occur and how many chunks were read?",
                        "What was the estimated cost of the March 2026 security incident?",
                        "How many audit findings were there in Q1 2026, and how many were High severity?",
                        "What is the projected ARR for December 2027 in the base-case budget scenario?",
                        "What was the Board-approved Project Atlas budget for FY 2026?",
                        "What are the two High-rated infrastructure risks from the Q2 2026 assessment?",
                        "What are the two strategic partnership deals and their proposed ARR values?",
                    ]},
                    "",
                    "<b>Category D — Cross-Document Conflicts</b>",
                    {"bullets": [
                        "When was Feature X originally scheduled to launch, and when is it actually launching? Which document is authoritative?",
                        "What is the Project Atlas FY 2026 budget according to the draft forecast vs the Board minutes? Which one is correct?",
                        "How does the competitive analysis describe SearchAI vs how is it described in the acquisition document?",
                        "What do the Board minutes say about Project Atlas adoption numbers vs the product analytics review?",
                    ]},
                    "",
                    "<b>Category E — Multi-Hop Reasoning</b>",
                    {"bullets": [
                        "What security incident triggered the Qdrant RBAC hardening, and what specific remediation measures were taken?",
                        "How does the Celery architecture improvement in Project Phoenix relate to the Q1 2026 audit findings?",
                        "What is the relationship between the Qdrant capacity risk (R02) and the budget adjustments approved by the Board?",
                        "Why is Feature X at risk, and what infrastructure changes are needed to mitigate the latency issue?",
                        "How did the onboarding redesign in February 2026 affect NPS, retention, and churn?",
                    ]},
                    "",
                    "<b>Category F — Classification Gating</b>",
                    {"bullets": [
                        "Ask 'What is the CEO's base salary?' as a viewer role — should return empty or no answer.",
                        "Ask 'What is the TAM for AI-powered enterprise search?' as a viewer role — should return the answer (public fact).",
                        "Ask 'What are the details of the SearchAI acquisition?' as a member role — should return no answer (confidential).",
                        "Ask 'What are the RAGAS scores?' as a member role — should return the answer (internal).",
                        "Ask 'What was the Series B mandate approved by the Board?' as an admin role — should return the answer (confidential).",
                    ]},
                    "",
                    "<b>Category G — Comparative & Analytical</b>",
                    {"bullets": [
                        "How does NovaTech's retrieval accuracy (NDCG@10) compare to Glean's?",
                        "Which customer segment has the highest ARR concentration and what is its percentage?",
                        "Compare the FinCorp pilot pricing ($48K/year for 1.2M queries) to standard Growth tier pricing.",
                        "How does Mid-Market Atlas adopter expansion NRR compare to non-Atlas Mid-Market accounts?",
                        "What is the combined annualized risk to ARR if both RetailMax and FinCorp deals are delayed?",
                    ]},
                ],
            },
            # ─────────────────────────────────────────────────────────────────
            # SECTION 7 — Scoring Template
            # ─────────────────────────────────────────────────────────────────
            {
                "heading": "7. Q&A Scoring Template",
                "content": [
                    "For each question, record:",
                    {"table": (
                        ["#", "Category", "Question", "Expected", "Actual", "Pass?"],
                        [
                            ["A1", "Simple (Eng)", "When was Project Atlas announced?", "Jan 15, 2026", "", ""],
                            ["A2", "Simple (Eng)", "What middleware does FastAPI use?", "CorrelationID, Auth, RateLimit, Compression", "", ""],
                            ["A3", "Simple (Eng)", "Qdrant chunks and collections?", "~2.4M / 4 collections", "", ""],
                            ["A4", "Simple (Eng)", "HNSW params?", "m=16, ef_construct=200, ef=128", "", ""],
                            ["A5", "Simple (Eng)", "Embedding model + dims?", "BAAI/bge-base-en-v1.5 / 768", "", ""],
                            ["A6", "Simple (Eng)", "Hybrid retrieval pipeline?", "Dense 40 + Sparse 40 → RRF k=60 → rerank top-20 → top-5", "", ""],
                            ["A7", "Simple (Eng)", "RAGAS scores (June 2026)?", "F=0.89, AR=0.86, CP=0.82, CR=0.79", "", ""],
                            ["A8", "Simple (Eng)", "Retrieval review trigger?", "Drop >0.05 in 7 days; last Jun 10 2026", "", ""],
                            ["A9", "Simple (Eng)", "Redis cluster config?", "3-node r7g.large, 3 shards, 18 GB", "", ""],
                            ["A10", "Simple (Eng)", "Celery ingest/rerank concurrency?", "ingest=4, rerank=8", "", ""],
                            ["A11", "Simple (Eng)", "/ask P50 latency + RPS?", "210 ms / 340 RPS on m6i.2xlarge", "", ""],
                            ["A12", "Simple (Eng)", "EKS clusters + DR parity?", "us-east-1 / eu-west-1, 60% parity", "", ""],
                            ["A13", "Simple (Eng)", "API versioning scheme?", "URI /vN/, RFC 8594, 180-day deprecation", "", ""],
                            ["A14", "Simple (Eng)", "CI/CD deploy strategy?", "ArgoCD canary 5→25→100%", "", ""],
                            ["A15", "Simple (Eng)", "NDCG@10 of chosen model?", "0.74", "", ""],
                            ["B1", "Simple (Prod)", "Q3 2026 roadmap themes?", "Atlas GA, Analytics Dashboard, Phoenix, SOC 2", "", ""],
                            ["B2", "Simple (Prod)", "Growth tier price + queries?", "$299/mo, 10,000 queries", "", ""],
                            ["B3", "Simple (Prod)", "NPS Q1 2026?", "44 (up from 31 YoY)", "", ""],
                            ["B4", "Simple (Prod)", "Q&A feature request %?", "68% of Growth customers", "", ""],
                            ["B5", "Simple (Prod)", "Query volume growth?", "50% QoQ, 4.2M/mo", "", ""],
                            ["B6", "Simple (Prod)", "Day-30 retention before/after?", "38% → 51% after Feb 2026 redesign", "", ""],
                            ["B7", "Simple (Prod)", "Answer Not Found rate drop?", "18% → 6% after hybrid retrieval", "", ""],
                            ["B8", "Simple (Prod)", "TAM of enterprise search?", "$4.2B, 38% CAGR", "", ""],
                            ["B9", "Simple (Prod)", "SOC 2 requirement %?", "67% (up from 48% in 2025)", "", ""],
                            ["B10", "Simple (Prod)", "Monthly churn vs target?", "2.1% actual vs 1.5% target", "", ""],
                            ["C1", "Simple (Conf)", "CEO salary + bonus?", "$420K base, 80% target bonus", "", ""],
                            ["C2", "Simple (Conf)", "Equity refreshes eligible?", "84 employees, $4.2M RSU budget", "", ""],
                            ["C3", "Simple (Conf)", "SearchAI codename?", "Project Nightingale", "", ""],
                            ["C4", "Simple (Conf)", "March incident date + chunks?", "2026-03-14, ~4,200 chunks", "", ""],
                            ["C5", "Simple (Conf)", "Incident cost estimate?", "$340,000", "", ""],
                            ["C6", "Simple (Conf)", "Audit findings?", "8 total, 2 High, 4 Med, 2 Low", "", ""],
                            ["C7", "Simple (Conf)", "Projected FY2027 ARR?", "$22M (base scenario)", "", ""],
                            ["C8", "Simple (Conf)", "Board-approved Atlas budget?", "$2.8M (amended from $2.4M)", "", ""],
                            ["C9", "Simple (Conf)", "Top2 infra risks?", "R01: single-region DR @60%; R02: Qdrant 78% → 90% by Jul", "", ""],
                            ["C10", "Simple (Conf)", "Partnership deals + ARR?", "FinCorp $480K/yr, RetailMax $180K/yr, combined $2.1M", "", ""],
                            ["D1", "Conflict", "Feature X launch discrepancy?", "Roadmap Jul vs Launch Plan Aug. LP authoritative.", "", ""],
                            ["D2", "Conflict", "Atlas budget discrepancy?", "Draft $2.4M vs Board $2.8M. Board authoritative.", "", ""],
                            ["D3", "Conflict", "SearchAI competitor vs acquisition?", "Comp report = competitor; Conf report = acquisition target", "", ""],
                            ["D4", "Conflict", "Beta user count match?", "Board: 34 enterprise; Analytics: 34 beta accounts ✓", "", ""],
                            ["E1", "Multi-hop", "Incident → remediation chain?", "March incident → mTLS, key rotation, NetworkPolicy, security gates", "", ""],
                            ["E2", "Multi-hop", "Phoenix + audit connection?", "Phoenix consolidates cron jobs; audit sought better automation", "", ""],
                            ["E3", "Multi-hop", "Qdrant capacity + budget link?", "78%→90% risk → Board amended budget to $2.8M for expansion", "", ""],
                            ["E4", "Multi-hop", "Feature X latency + infra?", ">500ms P95 → needs GPU scaling; budget $2.4M allocated", "", ""],
                            ["E5", "Multi-hop", "Feb redesign → total impact?", "Onboarding redesign → retention 38→51%, NPS 31→44, churn 2.1%", "", ""],
                            ["F1", "Gating", "CEO salary as viewer?", "No answer (confidential)", "", ""],
                            ["F2", "Gating", "TAM as viewer?", "$4.2B (public)", "", ""],
                            ["F3", "Gating", "SearchAI acquisition as member?", "No answer (confidential)", "", ""],
                            ["F4", "Gating", "RAGAS scores as member?", "F=0.89, etc. (internal)", "", ""],
                            ["F5", "Gating", "Series B mandate as admin?", "$14-20M via Goldman Sachs (confidential, admin OK)", "", ""],
                            ["G1", "Compare", "NDCG@10 Atlas vs Glean?", "0.74 vs 0.69", "", ""],
                            ["G2", "Compare", "Highest ARR segment?", "Enterprise: 10% accounts, 61% ARR", "", ""],
                            ["G3", "Compare", "FinCorp vs Growth pricing?", "$48K/yr for 1.2M = $0.04/query vs Growth $0.03/query", "", ""],
                            ["G4", "Compare", "Mid-Market Atlas vs non-Atlas NRR?", "$8,200 vs $1,950 (4.2× higher)", "", ""],
                            ["G5", "Compare", "Combined partnership risk?", "$2.1M ARR at risk if both delayed", "", ""],
                        ],
                        [0.4*8, 1.0*8, 3.5*8, 2.5*8, 1.8*8, 0.8*8],
                    )},
                ],
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive RAG evaluation PDF against 30-doc corpus"
    )
    parser.add_argument("output", nargs="?", default="data/eval_guide.pdf",
                        help="Output PDF path (default: data/eval_guide.pdf)")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    doc_data = generate()
    write_pdf(
        args.output,
        {k: doc_data[k] for k in ("title", "author", "department", "classification", "date")},
        doc_data["sections"],
    )

    print(f"\n{'='*60}")
    print(f"  Evaluation guide generated: {args.output}")
    print(f"  Classification: {doc_data['classification']}")
    print(f"  Total questions: 49 (15 Eng + 10 Prod + 10 Conf + 4 Conflict")
    print(f"                   + 5 Multi-hop + 5 Gating + 5 Compare)")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"  1. Upload the 30-corpus PDFs to a Qdrant collection")
    print(f"  2. Upload this evaluation guide (or keep as reference)")
    print(f"  3. Ask each question via the RAG /ask endpoint")
    print(f"  4. Record actual answers and Pass/Fail in the scoring template")
    print(f"  5. Test with multiple user roles to validate RBAC gating\n")


if __name__ == "__main__":
    main()
