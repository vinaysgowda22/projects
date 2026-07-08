"""Failed emails API routes."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_session
from backend.repositories.failed_email_repository import FailedEmailRepository

router = APIRouter()


class FailedEmailResponse(BaseModel):
    """Schema for failed email response."""

    id: int
    gmail_id: Optional[str]
    sender: Optional[str]
    subject: Optional[str]
    error_message: str
    processed_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[FailedEmailResponse])
async def list_failed_emails(limit: int = 100):
    """List all failed emails."""
    with get_session().__enter__() as session:
        repo = FailedEmailRepository(session)
        emails = repo.get_all(limit=limit)
        return [FailedEmailResponse.model_validate(email) for email in emails]


@router.get("/{email_id}", response_model=FailedEmailResponse)
async def get_failed_email(email_id: int):
    """Get a specific failed email by ID."""
    with get_session().__enter__() as session:
        repo = FailedEmailRepository(session)
        email = repo.get_by_id(email_id)

        if not email:
            raise HTTPException(status_code=404, detail="Failed email not found")

        return FailedEmailResponse.model_validate(email)


@router.delete("/{email_id}")
async def delete_failed_email(email_id: int):
    """Delete a failed email."""
    with get_session().__enter__() as session:
        repo = FailedEmailRepository(session)
        email = repo.get_by_id(email_id)

        if not email:
            raise HTTPException(status_code=404, detail="Failed email not found")

        repo.delete(email)
        return {"message": "Failed email deleted successfully"}
