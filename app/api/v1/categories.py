from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import User, Category
from app.schemas import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all categories (system + user's custom)."""
    categories = (
        db.query(Category)
        .filter(
            (Category.user_id == current_user.id) |
            (Category.is_system == True)
        )
        .order_by(Category.is_system.desc(), Category.name)
        .all()
    )
    return categories


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a custom category."""
    # Check for duplicate name
    existing = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.name == category_data.name,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )

    category = Category(
        user_id=current_user.id,
        name=category_data.name,
        type=category_data.type,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a custom category."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
        Category.is_system == False,
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or cannot be modified",
        )

    if category_data.name is not None:
        category.name = category_data.name
    if category_data.type is not None:
        category.type = category_data.type

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a custom category."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
        Category.is_system == False,
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or cannot be deleted",
        )

    db.delete(category)
    db.commit()
