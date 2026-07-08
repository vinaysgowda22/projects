"""Gmail service for fetching and syncing emails."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from backend.config import get_config


class GmailService:
    """Service for interacting with Gmail API with OAuth2 and Keychain integration."""
    
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    KEYCHAIN_SERVICE = "expense_intelligence"
    KEYCHAIN_USERNAME = "gmail_token"
    
    def __init__(self, credentials_path: Optional[Path] = None):
        """Initialize Gmail service.
        
        Args:
            credentials_path: Path to OAuth credentials JSON file.
        """
        config = get_config()
        self.credentials_path = credentials_path or Path(config.gmail.credentials_path)
        self.service = None
        self._rate_limit_delay = 0.1  # 100ms between requests to avoid rate limits
    
    def authenticate(self) -> Credentials:
        """Authenticate with Gmail API using OAuth2 and Keychain.
        
        Returns:
            Authenticated credentials object.
        """
        # Try to get credentials from Keychain first
        creds = self._get_credentials_from_keychain()
        
        if creds and creds.valid:
            logger.info("Using valid credentials from Keychain")
            return creds
        
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                creds.refresh(Request())
                self._save_credentials_to_keychain(creds)
                return creds
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
        
        # Load from credentials file for new authentication
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail credentials file not found: {self.credentials_path}. "
                "Please create OAuth credentials from Google Cloud Console."
            )
        
        with open(self.credentials_path) as f:
            credentials_data = json.load(f)
        
        # Create flow from credentials file
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_config(
            credentials_data,
            self.SCOPES
        )
        
        # Run local server for OAuth callback
        creds = flow.run_local_server(port=0)
        
        # Save to Keychain
        self._save_credentials_to_keychain(creds)
        
        logger.info("Successfully authenticated and saved credentials to Keychain")
        return creds
    
    def _get_credentials_from_keychain(self) -> Optional[Credentials]:
        """Get credentials from macOS Keychain.
        
        Returns:
            Credentials object if found, None otherwise.
        """
        try:
            token_json = keyring.get_password(
                self.KEYCHAIN_SERVICE,
                self.KEYCHAIN_USERNAME
            )
            if token_json:
                token_data = json.loads(token_json)
                return Credentials.from_authorized_user_info(token_data)
        except Exception as e:
            logger.debug(f"Could not get credentials from Keychain: {e}")
        return None
    
    def _save_credentials_to_keychain(self, creds: Credentials) -> None:
        """Save credentials to macOS Keychain.
        
        Args:
            creds: Credentials object to save.
        """
        try:
            token_json = creds.to_json()
            keyring.set_password(
                self.KEYCHAIN_SERVICE,
                self.KEYCHAIN_USERNAME,
                token_json
            )
            logger.info("Saved credentials to Keychain")
        except Exception as e:
            logger.warning(f"Could not save credentials to Keychain: {e}")
    
    def get_service(self):
        """Get authenticated Gmail API service.
        
        Returns:
            Gmail API service object.
        """
        if self.service is None:
            creds = self.authenticate()
            self.service = build("gmail", "v1", credentials=creds)
        return self.service
    
    def get_history_id(self) -> Optional[str]:
        """Get the last synced historyId from settings.
        
        Returns:
            History ID string or None if not set.
        """
        from backend.repositories.setting_repository import SettingRepository
        from backend.database import get_session
        
        with get_session().__enter__() as session:
            setting_repo = SettingRepository(session)
            setting = setting_repo.get_by_key("gmail_history_id")
            return setting.value if setting else None
    
    def set_history_id(self, history_id: str) -> None:
        """Save the last synced historyId to settings.
        
        Args:
            history_id: History ID string to save.
        """
        from backend.repositories.setting_repository import SettingRepository
        from backend.database import get_session
        
        with get_session().__enter__() as session:
            setting_repo = SettingRepository(session)
            setting_repo.upsert("gmail_history_id", history_id)
            logger.info(f"Saved historyId: {history_id}")
    
    def fetch_emails(
        self,
        query: str = "",
        max_results: int = 100,
        since_history_id: Optional[str] = None,
    ) -> list[dict]:
        """Fetch emails from Gmail with optional query and pagination.
        
        Args:
            query: Gmail search query (e.g., "from:alerts@hdfcbank.com").
            max_results: Maximum number of emails to fetch.
            since_history_id: If provided, fetch only emails since this historyId.
        
        Returns:
            List of email dictionaries with id, sender, subject, body, etc.
        """
        service = self.get_service()
        emails = []
        
        try:
            if since_history_id:
                # Use history API for incremental sync
                emails = self._fetch_emails_by_history(since_history_id, max_results)
            else:
                # Use list API for initial sync
                emails = self._fetch_emails_by_list(query, max_results)
            
            logger.info(f"Fetched {len(emails)} emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
    
    def _fetch_emails_by_list(self, query: str, max_results: int) -> list[dict]:
        """Fetch emails using Gmail list API with pagination.
        
        Args:
            query: Gmail search query.
            max_results: Maximum number of emails to fetch.
        
        Returns:
            List of email dictionaries.
        """
        service = self.get_service()
        emails = []
        page_token = None
        
        while True:
            time.sleep(self._rate_limit_delay)
            
            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=min(max_results, 50),  # Gmail API limit per page
                pageToken=page_token,
            ).execute()
            
            messages = result.get("messages", [])
            
            for msg in messages:
                email = self._get_message_details(msg["id"])
                if email:
                    emails.append(email)
                    if len(emails) >= max_results:
                        return emails
            
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        
        return emails
    
    def _fetch_emails_by_history(self, history_id: str, max_results: int) -> list[dict]:
        """Fetch emails using Gmail history API for incremental sync.
        
        Args:
            history_id: Starting history ID.
            max_results: Maximum number of emails to fetch.
        
        Returns:
            List of email dictionaries.
        """
        service = self.get_service()
        emails = []
        current_history_id = history_id
        
        while len(emails) < max_results:
            time.sleep(self._rate_limit_delay)
            
            try:
                history = service.users().history().list(
                    userId="me",
                    startHistoryId=current_history_id,
                ).execute()
                
                history_items = history.get("history", [])
                
                if not history_items:
                    break
                
                for item in history_items:
                    messages_added = item.get("messagesAdded", [])
                    for msg_added in messages_added:
                        msg_id = msg_added["message"]["id"]
                        email = self._get_message_details(msg_id)
                        if email:
                            emails.append(email)
                            if len(emails) >= max_results:
                                return emails
                
                current_history_id = history_items[-1]["id"]
                
            except HttpError as e:
                if e.resp.status == 404:
                    logger.warning(f"History ID {current_history_id} not found, may be too old")
                    break
                raise
        
        return emails
    
    def _get_message_details(self, message_id: str) -> Optional[dict]:
        """Get full message details including body.
        
        Args:
            message_id: Gmail message ID.
        
        Returns:
            Email dictionary with id, sender, subject, body, etc.
        """
        service = self.get_service()
        
        try:
            time.sleep(self._rate_limit_delay)
            
            msg = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            
            # Extract body from message parts
            body = self._extract_body(msg.get("payload", {}))
            
            return {
                "gmail_id": msg["id"],
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "history_id": msg.get("historyId"),
            }
            
        except HttpError as e:
            logger.warning(f"Failed to get message {message_id}: {e}")
            return None
    
    def _extract_body(self, payload: dict) -> str:
        """Extract email body from message payload.
        
        Args:
            payload: Gmail message payload.
        
        Returns:
            Email body text.
        """
        body = ""
        
        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        import base64
                        body += base64.urlsafe_b64decode(data).decode("utf-8")
                elif "parts" in part:
                    # Recursively extract from nested parts
                    body += self._extract_body(part)
        else:
            # Single part message
            data = payload.get("body", {}).get("data", "")
            if data:
                import base64
                body = base64.urlsafe_b64decode(data).decode("utf-8")
        
        return body
    
    def sync_emails(
        self,
        query: str = "",
        max_results: int = 100,
    ) -> list[dict]:
        """Sync emails with incremental history tracking.
        
        Args:
            query: Gmail search query.
            max_results: Maximum number of emails to fetch.
        
        Returns:
            List of new email dictionaries.
        """
        history_id = self.get_history_id()
        
        if history_id:
            logger.info(f"Syncing emails since historyId: {history_id}")
            emails = self.fetch_emails(query, max_results, since_history_id=history_id)
        else:
            logger.info("No historyId found, performing initial sync")
            emails = self.fetch_emails(query, max_results)
        
        # Update historyId if we got new emails
        if emails:
            latest_history_id = max(
                email.get("history_id", "") for email in emails if email.get("history_id")
            )
            if latest_history_id:
                self.set_history_id(latest_history_id)
        
        return emails


# Global service instance
_service: Optional[GmailService] = None


def get_gmail_service() -> GmailService:
    """Get the global Gmail service instance (singleton pattern)."""
    global _service
    if _service is None:
        _service = GmailService()
    return _service


def reset_gmail_service() -> None:
    """Reset the global Gmail service (useful for testing)."""
    global _service
    _service = None
