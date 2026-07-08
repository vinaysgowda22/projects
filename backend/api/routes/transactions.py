"""Transactions API routes."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.categorization import get_category_classifier
from backend.database import get_session
from backend.repositories.transaction_repository import TransactionRepository

router = APIRouter()


class CategoryCorrection(BaseModel):
    """Schema for correcting a transaction's category."""

    category: str


class TransactionCreate(BaseModel):
    """Schema for creating a transaction."""

    transaction_date: datetime
    amount: Decimal
    merchant: str
    category: Optional[str] = None
    account_id: int
    reference_number: Optional[str] = None
    gmail_id: Optional[str] = None
    transaction_type: str = "debit"
    status: str = "posted"
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    id: int
    transaction_date: datetime
    amount: Decimal
    merchant: str
    category: Optional[str]
    account_id: int
    reference_number: Optional[str]
    gmail_id: Optional[str]
    transaction_type: str
    status: str
    description: Optional[str]
    is_duplicate: bool
    possible_duplicate: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=TransactionResponse)
async def create_transaction(transaction: TransactionCreate):
    """Create a new transaction."""
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)

        new_transaction = repo.create(
            transaction_date=transaction.transaction_date,
            amount=transaction.amount,
            merchant=transaction.merchant,
            category=transaction.category,
            account_id=transaction.account_id,
            reference_number=transaction.reference_number,
            gmail_id=transaction.gmail_id,
            transaction_type=transaction.transaction_type,
            status=transaction.status,
            description=transaction.description,
        )

        return TransactionResponse.model_validate(new_transaction)


@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    merchant: Optional[str] = None,
    category: Optional[str] = None,
):
    """List transactions with optional filters."""
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)

        if merchant or category:
            transactions = repo.search(
                merchant=merchant,
                category=category,
                limit=limit,
            )
        else:
            transactions = repo.get_all(limit=limit, offset=offset)

        return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int):
    """Get a specific transaction by ID."""
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)
        transaction = repo.get_by_id(transaction_id)

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return TransactionResponse.model_validate(transaction)


@router.patch("/{transaction_id}/category", response_model=TransactionResponse)
async def correct_transaction_category(
    transaction_id: int, correction: CategoryCorrection
):
    """Correct a transaction's category and learn the merchant mapping.

    The corrected category is applied to this transaction and persisted as a
    learned merchant->category mapping (spec §6.5), so future transactions from
    the same merchant are categorized the same way without asking again.
    """
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)
        transaction = repo.get_by_id(transaction_id)

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        updated = repo.update(transaction, category=correction.category)
        get_category_classifier().learn(updated.merchant, correction.category)

        return TransactionResponse.model_validate(updated)


@router.get("/recent/", response_model=List[TransactionResponse])
async def get_recent_transactions(limit: int = Query(50, ge=1, le=100)):
    """Get recent transactions."""
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)
        transactions = repo.get_recent(limit=limit)
        return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.get("/by-merchant/{merchant}", response_model=List[TransactionResponse])
async def get_transactions_by_merchant(
    merchant: str, limit: int = Query(100, ge=1, le=100)
):
    """Get transactions by merchant name."""
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)
        transactions = repo.get_by_merchant(merchant, limit=limit)
        return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.get("/by-category/{category}", response_model=List[TransactionResponse])
async def get_transactions_by_category(
    category: str, limit: int = Query(100, ge=1, le=100)
):
    """Get transactions by category."""
    with get_session().__enter__() as session:
        repo = TransactionRepository(session)
        transactions = repo.get_by_category(category, limit=limit)
        return [TransactionResponse.model_validate(tx) for tx in transactions]
