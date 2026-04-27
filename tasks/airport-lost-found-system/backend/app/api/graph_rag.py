from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_staff
from app.models import User
from app.schemas import GraphContextResponse, GraphExplainRequest
from app.services.graph_context_service import graph_context_service


router = APIRouter(prefix="/graph-rag", tags=["graph rag"])


@router.get("/matches/{match_id}", response_model=GraphContextResponse)
async def match_graph_context(
    match_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    try:
        return await graph_context_service.match_context(db, match_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")


@router.post("/matches/{match_id}/explain", response_model=GraphContextResponse)
async def explain_match_graph(
    match_id: int,
    payload: GraphExplainRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    try:
        return await graph_context_service.match_context(db, match_id, payload.question)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")


@router.get("/found-items/{item_id}", response_model=GraphContextResponse)
async def found_item_graph_context(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    try:
        return await graph_context_service.found_item_context(db, item_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")


@router.get("/lost-reports/{report_id}", response_model=GraphContextResponse)
async def lost_report_graph_context(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    try:
        return await graph_context_service.lost_report_context(db, report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lost report not found")
