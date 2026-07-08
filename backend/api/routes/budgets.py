"""Budgets API routes."""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_session
from backend.repositories.budget_repository import BudgetRepository

router = APIRouter()


class BudgetCreate(BaseModel):
    """Schema for creating or updating a budget."""

    category: str
    amount: Decimal
    period: str = "monthly"


class BudgetUpdate(BaseModel):
    """Schema for patching a budget."""

    amount: Optional[Decimal] = None
    period: Optional[str] = None
    is_active: Optional[bool] = None


class BudgetResponse(BaseModel):
    """Schema for budget response."""

    id: int
    category: str
    amount: Decimal
    period: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=BudgetResponse)
async def create_budget(budget: BudgetCreate):
    """Create a budget (or update the existing one for the category/period)."""
    with get_session().__enter__() as session:
        repo = BudgetRepository(session)
        saved = repo.upsert(
            category=budget.category, amount=budget.amount, period=budget.period
        )
        return BudgetResponse.model_validate(saved)


@router.get("/", response_model=List[BudgetResponse])
async def list_budgets(active_only: bool = Query(False)):
    """List budgets, optionally only active ones."""
    with get_session().__enter__() as session:
        repo = BudgetRepository(session)
        budgets = repo.get_active() if active_only else repo.get_all()
        return [BudgetResponse.model_validate(b) for b in budgets]


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(budget_id: int):
    """Get a specific budget by ID."""
    with get_session().__enter__() as session:
        repo = BudgetRepository(session)
        budget = repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        return BudgetResponse.model_validate(budget)


@router.get("/by-category/{category}", response_model=BudgetResponse)
async def get_budget_by_category(category: str, period: str = "monthly"):
    """Get the budget for a category and period."""
    with get_session().__enter__() as session:
        repo = BudgetRepository(session)
        budget = repo.get_by_category(category, period)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        return BudgetResponse.model_validate(budget)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(budget_id: int, update: BudgetUpdate):
    """Update fields on a budget."""
    with get_session().__enter__() as session:
        repo = BudgetRepository(session)
        budget = repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        fields = update.model_dump(exclude_none=True)
        updated = repo.update(budget, **fields) if fields else budget
        return BudgetResponse.model_validate(updated)


@router.delete("/{budget_id}")
async def delete_budget(budget_id: int):
    """Delete a budget."""
    with get_session().__enter__() as session:
        repo = BudgetRepository(session)
        budget = repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        repo.delete(budget)
        return {"message": "Budget deleted successfully"}
