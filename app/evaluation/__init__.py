"""RAGAS evaluation module for RAG pipeline quality assessment.

Provides dataset generation, metric computation, and CI gate integration.
Metrics: faithfulness, answer relevancy, context precision, context recall.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

# Target thresholds for CI gate
DEFAULT_THRESHOLDS = {
    "faithfulness": 0.80,
    "answer_relevancy": 0.75,
    "context_precision": 0.70,
    "context_recall": 0.70,
}


@dataclass
class EvalSample:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    sample: EvalSample
    scores: dict[str, float]
    passed: bool


@dataclass
class EvaluationReport:
    results: list[EvalResult]
    aggregate: dict[str, float]
    passed: bool
    thresholds: dict[str, float]


def load_golden_dataset(path: str) -> list[EvalSample]:
    """Load a golden test dataset from a JSON file.

    Format:
    [
        {
            "question": "...",
            "answer": "...",
            "contexts": ["...", "..."],
            "ground_truth": "...",
            "metadata": {}
        }
    ]
    """
    if not os.path.exists(path):
        logger.warning("Golden dataset not found at %s", path)
        return []

    with open(path) as f:
        data = json.load(f)

    samples = []
    for item in data:
        samples.append(
            EvalSample(
                question=item["question"],
                answer=item.get("answer", ""),
                contexts=item.get("contexts", []),
                ground_truth=item.get("ground_truth", ""),
                metadata=item.get("metadata", {}),
            )
        )
    logger.info("Loaded %d evaluation samples from %s", len(samples), path)
    return samples


def save_golden_dataset(samples: list[EvalSample], path: str) -> None:
    """Save evaluation samples as a golden dataset JSON file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = [
        {
            "question": s.question,
            "answer": s.answer,
            "contexts": s.contexts,
            "ground_truth": s.ground_truth,
            "metadata": s.metadata,
        }
        for s in samples
    ]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Saved %d evaluation samples to %s", len(samples), path)


async def compute_ragas_metrics(
    samples: list[EvalSample],
    llm_config: dict[str, Any] | None = None,
) -> EvaluationReport:
    """Compute RAGAS metrics for a set of evaluation samples.

    Requires a running LLM endpoint (the judge) specified in settings or llm_config.
    llm_config can override: base_url, api_key, model
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as e:
        logger.error("RAGAS not installed: %s", e)
        return EvaluationReport(results=[], aggregate={}, passed=False, thresholds=DEFAULT_THRESHOLDS)

    eval_llm = _build_ragas_llm(llm_config)

    # Build HuggingFace dataset from samples
    data = {
        "question": [s.question for s in samples],
        "answer": [s.answer for s in samples],
        "contexts": [s.contexts for s in samples],
        "ground_truth": [s.ground_truth for s in samples],
    }
    dataset = Dataset.from_dict(data)

    # Run evaluation
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=eval_llm,
    )

    # Build per-sample results
    df = result.to_pandas()
    per_sample: list[EvalResult] = []
    aggregate: dict[str, float] = {}

    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        if metric_name in df.columns:
            values = df[metric_name].dropna().tolist()
            aggregate[metric_name] = sum(values) / len(values) if values else 0.0

    for i, sample in enumerate(samples):
        scores = {}
        for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            if metric_name in df.columns and i < len(df):
                scores[metric_name] = float(df.iloc[i][metric_name]) if pd.notna(df.iloc[i][metric_name]) else 0.0
        passed = all(scores.get(k, 0.0) >= v for k, v in DEFAULT_THRESHOLDS.items())
        per_sample.append(EvalResult(sample=sample, scores=scores, passed=passed))

    overall_passed = all(aggregate.get(k, 0.0) >= v for k, v in DEFAULT_THRESHOLDS.items())

    return EvaluationReport(
        results=per_sample,
        aggregate=aggregate,
        passed=overall_passed,
        thresholds=DEFAULT_THRESHOLDS,
    )


def _build_ragas_llm(llm_config: dict[str, Any] | None = None) -> Any:
    """Build a RAGAS-compatible LLM wrapper from config."""
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    cfg = llm_config or {}
    base_url = cfg.get("base_url", settings.LLM_BASE_URL)
    api_key = cfg.get("api_key", settings.LLM_API_KEY or "")
    model = cfg.get("model", settings.LLM_MODEL)

    chat = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=0.0,
    )
    return LangchainLLMWrapper(chat)
