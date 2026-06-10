#!/usr/bin/env python
"""CI evaluation gate — runs RAGAS on the golden dataset and fails if below thresholds.

Usage:
    python scripts/ci_eval.py                        # uses default golden dataset
    python scripts/ci_eval.py --dataset path/to/data.json
    python scripts/ci_eval.py --thresholds '{"faithfulness": 0.85}'
"""
import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="RAGAS CI evaluation gate")
    parser.add_argument(
        "--dataset",
        default="data/golden_dataset.json",
        help="Path to golden dataset JSON",
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
    )

    samples = load_golden_dataset(args.dataset)
    if not samples:
        logger.error("No evaluation samples found in %s", args.dataset)
        sys.exit(1)

    thresholds = DEFAULT_THRESHOLDS.copy()
    if args.thresholds:
        thresholds.update(json.loads(args.thresholds))

    report = await compute_ragas_metrics(samples)
    report.thresholds = thresholds

    # Recompute pass/fail with custom thresholds
    report.passed = all(
        report.aggregate.get(k, 0.0) >= v for k, v in thresholds.items()
    )
    for r in report.results:
        r.passed = all(
            r.scores.get(k, 0.0) >= v for k, v in thresholds.items()
        )

    # Print summary
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
    import asyncio
    asyncio.run(main())
