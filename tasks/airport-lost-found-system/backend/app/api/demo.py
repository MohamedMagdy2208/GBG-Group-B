from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rbac import require_admin
from app.models import User
from app.services.demo_scenario_service import demo_scenario_service


router = APIRouter(prefix="/admin/demo", tags=["demo"])


def _ensure_demo_environment() -> None:
    settings = get_settings()
    if settings.environment.lower() in {"production", "prod"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo simulator is disabled in production")


@router.get("/scenarios")
def list_scenarios(_: User = Depends(require_admin)) -> dict:
    _ensure_demo_environment()
    return {"scenarios": demo_scenario_service.list_scenarios()}


@router.get("/runs")
def list_runs(_: User = Depends(require_admin)) -> dict:
    _ensure_demo_environment()
    return {"runs": demo_scenario_service.list_runs()}


@router.post("/scenarios/{scenario_key}")
async def start_scenario(
    scenario_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    _ensure_demo_environment()
    try:
        run = await demo_scenario_service.start(db, scenario_key, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return run.to_dict()


@router.get("/runs/{run_id}")
def get_run(run_id: str, _: User = Depends(require_admin)) -> dict:
    _ensure_demo_environment()
    run = demo_scenario_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run.to_dict()


@router.delete("/runs/{run_id}")
def cleanup_run(
    run_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    _ensure_demo_environment()
    try:
        return demo_scenario_service.cleanup(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
