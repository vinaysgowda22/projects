"""Accounts API routes."""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.models.account import Account
from backend.repositories.account_repository import AccountRepository


router = APIRouter()


class AccountCreate(BaseModel):
    """Schema for creating an account."""
    bank_name: str
    account_identifier: str
    account_type: str = "savings"
    nickname: str


class AccountResponse(BaseModel):
    """Schema for account response."""
    id: int
    bank_name: str
    account_identifier: str
    account_type: str
    nickname: str
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=AccountResponse)
async def create_account(account: AccountCreate):
    """Create a new account."""
    with get_session().__enter__() as session:
        repo = AccountRepository(session)
        
        # Check if account already exists
        existing = repo.get_by_identifier(account.bank_name, account.account_identifier)
        if existing:
            raise HTTPException(status_code=400, detail="Account already exists")
        
        new_account = repo.create(
            bank_name=account.bank_name,
            account_identifier=account.account_identifier,
            account_type=account.account_type,
            nickname=account.nickname,
        )
        
        return AccountResponse.model_validate(new_account)


@router.get("/", response_model=List[AccountResponse])
async def list_accounts():
    """List all accounts."""
    with get_session().__enter__() as session:
        repo = AccountRepository(session)
        accounts = repo.get_all()
        return [AccountResponse.model_validate(acc) for acc in accounts]


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int):
    """Get a specific account by ID."""
    with get_session().__enter__() as session:
        repo = AccountRepository(session)
        account = repo.get_by_id(account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return AccountResponse.model_validate(account)


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account: AccountCreate):
    """Update an account."""
    with get_session().__enter__() as session:
        repo = AccountRepository(session)
        existing = repo.get_by_id(account_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Account not found")
        
        updated = repo.update(
            existing,
            bank_name=account.bank_name,
            account_identifier=account.account_identifier,
            account_type=account.account_type,
            nickname=account.nickname,
        )
        
        return AccountResponse.model_validate(updated)


@router.delete("/{account_id}")
async def delete_account(account_id: int):
    """Delete an account."""
    with get_session().__enter__() as session:
        repo = AccountRepository(session)
        account = repo.get_by_id(account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        repo.delete(account)
        return {"message": "Account deleted successfully"}
