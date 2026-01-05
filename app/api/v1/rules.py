from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user
from app.models import User, CategorizationRule
from app.schemas import RuleCreate, RuleResponse
from app.services import CategorizationService

router = APIRouter()


@router.get("", response_model=List[RuleResponse])
def get_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all categorization rules (user's + system)."""
    rules = (
        db.query(CategorizationRule)
        .options(joinedload(CategorizationRule.category))
        .filter(
            (CategorizationRule.user_id == current_user.id) |
            (CategorizationRule.user_id.is_(None))
        )
        .order_by(
            CategorizationRule.user_id.desc().nullslast(),
            CategorizationRule.priority.desc(),
        )
        .all()
    )
    return rules


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    rule_data: RuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a categorization rule."""
    service = CategorizationService(db)

    try:
        rule = service.create_rule(
            user_id=current_user.id,
            category_id=rule_data.category_id,
            pattern=rule_data.pattern,
            match_type=rule_data.match_type,
            priority=rule_data.priority,
        )
        # Load category relationship
        db.refresh(rule, ["category"])
        return rule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a categorization rule (user rules only)."""
    service = CategorizationService(db)
    success = service.delete_rule(rule_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found or cannot be deleted",
        )


@router.post("/recategorize", status_code=status.HTTP_200_OK)
def recategorize_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recategorize all non-edited transactions based on current rules."""
    service = CategorizationService(db)
    updated_count = service.recategorize_transactions(current_user.id)

    return {
        "message": f"Recategorized {updated_count} transactions",
        "updated_count": updated_count,
    }
