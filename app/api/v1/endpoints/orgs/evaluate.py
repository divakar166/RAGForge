"""RAGAS evaluation endpoint — run quality metrics on the pipeline."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import OrganizationContext, get_org_context, require_org_role
from app.evaluation import (
    compute_ragas_metrics,
    load_golden_dataset,
    run_pipeline_for_samples,
    save_golden_dataset,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluate", tags=["orgs-evaluate"])


@router.post("/run")
async def run_evaluation(
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
):
    org_id = ctx.organization["id"]
    samples = load_golden_dataset(org_id=org_id)
    if not samples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No golden dataset found for this organization.",
        )

    logger.info("Running pipeline on %d samples for org %s", len(samples), org_id)
    samples = await run_pipeline_for_samples(samples, org_id=org_id)

    save_golden_dataset(samples, org_id=org_id)

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
    ctx: OrganizationContext = Depends(get_org_context),
):
    org_id = ctx.organization["id"]
    samples = load_golden_dataset(org_id=org_id)
    return {"organization_id": org_id, "name": "Golden Dataset", "size": len(samples)}
