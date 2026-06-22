#!/usr/bin/env python
"""CI evaluation gate — runs RAGAS on the golden dataset and fails if below thresholds.

Usage:
    python scripts/ci_eval.py [--org-id ORG_ID]
    python scripts/ci_eval.py --dataset path/to/data.json
    python scripts/ci_eval.py --thresholds '{"faithfulness": 0.85}'
"""
import argparse
import asyncio
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="RAGAS CI evaluation gate")
    parser.add_argument(
        "--org-id",
        default=None,
        help="Organization ID to scope dataset (default: global)",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to golden dataset JSON (overrides org-based path)",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        default=None,
        help='JSON string of per-metric thresholds, e.g. \'{"faithfulness": 0.85}\'',
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write evaluation report JSON",
    )
    args = parser.parse_args()

    from app.evaluation import (
        DEFAULT_THRESHOLDS,
        compute_ragas_metrics,
        load_golden_dataset,
        run_pipeline_for_samples,
        save_golden_dataset,
    )

    if args.dataset:
        samples = load_golden_dataset(path=args.dataset)
    else:
        samples = load_golden_dataset(org_id=args.org_id)

    if not samples:
        logger.error("No evaluation samples found")
        sys.exit(1)

    org_id_for_run = args.org_id or "global"
    logger.info("Running RAG pipeline on %d samples (org=%s)", len(samples), org_id_for_run)
    samples = await run_pipeline_for_samples(samples, org_id=org_id_for_run)
    if args.org_id:
        save_golden_dataset(samples, org_id=args.org_id)
    else:
        save_golden_dataset(samples)

    thresholds = DEFAULT_THRESHOLDS.copy()
    if args.thresholds:
        thresholds.update(json.loads(args.thresholds))

    report = await compute_ragas_metrics(samples)
    report.thresholds = thresholds

    report.passed = all(
        report.aggregate.get(k, 0.0) >= v for k, v in thresholds.items()
    )
    for r in report.results:
        r.passed = all(
            r.scores.get(k, 0.0) >= v for k, v in thresholds.items()
        )

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION REPORT")
    print("=" * 60)
    print(f"Samples: {len(samples)}")
    print(f"Overall: {'PASS' if report.passed else 'FAIL'}")
    print()
    print(f"{'Metric':<25} {'Score':<10} {'Threshold':<10} {'Status':<10}")
    print("-" * 55)
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        score = report.aggregate.get(metric, 0.0)
        threshold = thresholds.get(metric, 0.0)
        status = "PASS" if score >= threshold else "FAIL"
        print(f"{metric:<25} {score:<10.4f} {threshold:<10.2f} {status:<10}")
    print("=" * 60)

    if args.output:
        import os
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump({
                "passed": report.passed,
                "aggregate": report.aggregate,
                "thresholds": thresholds,
                "num_samples": len(samples),
            }, f, indent=2)
        logger.info("Report saved to %s", args.output)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
