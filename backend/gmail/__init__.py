"""Gmail sync service for fetching transaction emails."""

from backend.gmail.gmail_service import GmailService, get_gmail_service

__all__ = [
    "GmailService",
    "get_gmail_service",
]
