"""RAGAS evaluation endpoint — run quality metrics on the pipeline."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import OrganizationContext, get_org_context, require_org_role
from app.evaluation import compute_ragas_metrics, load_golden_dataset

router = APIRouter(prefix="/evaluate", tags=["orgs-evaluate"])


@router.post("/run")
async def run_evaluation(
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
):
    samples = load_golden_dataset("data/golden_dataset.json")
    if not samples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No golden dataset found.",
        )

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
    samples = load_golden_dataset("data/golden_dataset.json")
    return {"name": "Golden Dataset", "size": len(samples)}
