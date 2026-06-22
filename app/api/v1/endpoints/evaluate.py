"""RAGAS evaluation endpoint — run quality metrics on the pipeline."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.evaluation import (
    compute_ragas_metrics,
    load_golden_dataset,
    run_pipeline_for_samples,
    save_golden_dataset,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("/run")
async def run_evaluation(
    user: dict = Depends(get_current_user),
):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    samples = load_golden_dataset()
    if not samples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No golden dataset found.",
        )

    logger.info("Running pipeline on %d samples", len(samples))
    samples = await run_pipeline_for_samples(samples, org_id="global")

    save_golden_dataset(samples)

    report = await compute_ragas_metrics(samples)
    return [
        {
            "metric": name,
            "score": report.aggregate.get(name, 0),
            "threshold": report.thresholds.get(name, 0),
            "passed": report.aggregate.get(name, 0) >= report.thresholds.get(name, 0),
        }
        for name in report.aggregate
    ]


@router.get("/dataset")
async def get_dataset_info(
    user: dict = Depends(get_current_user),
):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    samples = load_golden_dataset()
    return {"name": "Golden Dataset", "size": len(samples)}
