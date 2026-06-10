"""RAGAS evaluation endpoint — run quality metrics on the pipeline."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.db.models.user import User
from app.evaluation import EvalSample, compute_ragas_metrics, load_golden_dataset
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

    return {
        "passed": report.passed,
        "aggregate": report.aggregate,
        "thresholds": report.thresholds,
        "num_samples": len(samples),
        "per_sample": [
            {
                "question": r.sample.question[:100],
                "scores": r.scores,
                "passed": r.passed,
            }
            for r in report.results
        ],
    }


@router.get("/dataset")
async def get_dataset_info(
    user: User = Depends(get_current_user),
):
    """Get info about the current golden dataset."""
    samples = load_golden_dataset("data/golden_dataset.json")
    return {
        "num_samples": len(samples),
        "samples": [
            {
                "question": s.question[:200],
                "has_ground_truth": bool(s.ground_truth),
                "num_contexts": len(s.contexts),
            }
            for s in samples
        ],
    }
