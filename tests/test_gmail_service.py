"""Tests for Gmail service."""

from unittest.mock import Mock, patch

from backend.gmail.gmail_service import (
    GmailService,
    get_gmail_service,
    reset_gmail_service,
)


class TestGmailService:
    """Test suite for GmailService."""

    def setup_method(self):
        """Reset service before each test."""
        reset_gmail_service()

    def test_singleton(self):
        """Test that global service is a singleton."""
        service1 = get_gmail_service()
        service2 = get_gmail_service()

        assert service1 is service2

    def test_keychain_service_name(self):
        """Test keychain service name is set correctly."""
        service = GmailService()
        assert service.KEYCHAIN_SERVICE == "expense_intelligence"
        assert service.KEYCHAIN_USERNAME == "gmail_token"

    def test_scopes(self):
        """Test Gmail API scopes are correct."""
        service = GmailService()
        assert "https://www.googleapis.com/auth/gmail.readonly" in service.SCOPES

    @patch("backend.gmail.gmail_service.keyring.get_password")
    def test_get_credentials_from_keychain_none(self, mock_get_password):
        """Test getting credentials when none exist in Keychain."""
        mock_get_password.return_value = None

        service = GmailService()
        creds = service._get_credentials_from_keychain()

        assert creds is None
        mock_get_password.assert_called_once()

    @patch("backend.gmail.gmail_service.keyring.get_password")
    @patch("backend.gmail.gmail_service.Credentials")
    def test_get_credentials_from_keychain_success(
        self, mock_credentials, mock_get_password
    ):
        """Test getting credentials from Keychain successfully."""
        mock_get_password.return_value = '{"token": "test"}'
        mock_creds = Mock()
        mock_credentials.from_authorized_user_info.return_value = mock_creds

        service = GmailService()
        creds = service._get_credentials_from_keychain()

        assert creds == mock_creds

    @patch("backend.gmail.gmail_service.keyring.set_password")
    def test_save_credentials_to_keychain(self, mock_set_password):
        """Test saving credentials to Keychain."""
        mock_creds = Mock()
        mock_creds.to_json.return_value = '{"token": "test"}'

        service = GmailService()
        service._save_credentials_to_keychain(mock_creds)

        mock_set_password.assert_called_once()

    def test_extract_body_single_part(self):
        """Test extracting body from single-part message."""
        service = GmailService()

        payload = {"body": {"data": "VGVzdCBib2R5"}}  # Base64 for "Test body"

        body = service._extract_body(payload)
        assert body == "Test body"

    def test_extract_body_multipart(self):
        """Test extracting body from multipart message."""
        service = GmailService()

        payload = {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "VGVzdCBib2R5"},  # Base64 for "Test body"
                }
            ]
        }

        body = service._extract_body(payload)
        assert body == "Test body"

    def test_extract_body_nested(self):
        """Test extracting body from nested multipart message."""
        service = GmailService()

        payload = {
            "parts": [
                {
                    "mimeType": "multipart/mixed",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": "VGVzdCBib2R5"},  # Base64 for "Test body"
                        }
                    ],
                }
            ]
        }

        body = service._extract_body(payload)
        assert body == "Test body"

    def test_extract_body_empty(self):
        """Test extracting body when no body data exists."""
        service = GmailService()

        payload = {}
        body = service._extract_body(payload)
        assert body == ""
