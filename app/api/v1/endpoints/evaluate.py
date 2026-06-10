"""RAGAS evaluation endpoint — run quality metrics on the pipeline."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.db.models.user import User
from app.evaluation import compute_ragas_metrics, load_golden_dataset
from app.services.rbac import has_any_permission

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("/run")
async def run_evaluation(
    user: User = Depends(get_current_user),
):
    """Run RAGAS evaluation on the golden dataset."""
    if not await has_any_permission(user, ["evaluate:run", "*:*"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    samples = load_golden_dataset("data/golden_dataset.json")
    if not samples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No golden dataset found. Create data/golden_dataset.json first.",
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
    user: User = Depends(get_current_user),
):
    """Get info about the current golden dataset."""
    samples = load_golden_dataset("data/golden_dataset.json")
    return {
        "name": "Golden Dataset",
        "size": len(samples),
    }
