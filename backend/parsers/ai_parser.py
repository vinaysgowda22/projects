"""AI fallback parser for emails that can't be parsed by regex-based parsers."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger
from openai import OpenAI

from backend.config import get_config
from backend.parsers.base import BaseParser, TransactionDraft


class AIParser(BaseParser):
    """AI-powered parser using OpenAI for emails that regex parsers can't handle."""

    def __init__(self):
        """Initialize the AI parser."""
        super().__init__()
        config = get_config()
        self.client = OpenAI(api_key=config.ai.api_key)
        self.model = config.ai.model

    def parse(self, email: dict) -> Optional[TransactionDraft]:
        """Parse email using AI to extract transaction data.

        Args:
            email: Email dictionary with keys: sender, subject, body, date.

        Returns:
            TransactionDraft if parsing successful, None otherwise.
        """
        try:
            # Step 1: Strip HTML to plain text
            plain_text = self._strip_html(email.get("body", ""))

            # Step 2: Build prompt for AI
            prompt = self._build_prompt(email, plain_text)

            # Step 3: Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial transaction extractor. Extract transaction data from bank emails and return as JSON.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )

            # Step 4: Parse AI response
            extracted_data = self._parse_ai_response(response)

            # Step 5: Validate extracted data
            if not self._validate_extracted_data(extracted_data):
                logger.warning("AI extracted invalid data")
                return None

            # Step 6: Create TransactionDraft
            draft = self._create_draft(email, extracted_data)

            logger.info(f"Successfully parsed email using AI: {email.get('gmail_id')}")
            return draft

        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            return None

    def _strip_html(self, html_content: str) -> str:
        """Strip HTML tags and extract plain text.

        Args:
            html_content: HTML content string.

        Returns:
            Plain text string.
        """
        if not html_content:
            return ""

        # Use BeautifulSoup to parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _build_prompt(self, email: dict, plain_text: str) -> str:
        """Build prompt for AI extraction.

        Args:
            email: Email dictionary.
            plain_text: Plain text body of email.

        Returns:
            Prompt string for AI.
        """
        prompt = f"""Extract transaction data from this bank email:

Sender: {email.get('sender', '')}
Subject: {email.get('subject', '')}
Date: {email.get('date', '')}

Email Body:
{plain_text}

Extract the following fields and return as JSON:
- amount: transaction amount as a number (positive for debits, negative for credits)
- merchant: merchant name or description
- transaction_date: date in YYYY-MM-DD format
- transaction_type: "debit" or "credit"
- reference_number: any reference number if present
- account_identifier: account identifier (e.g., last 4 digits of card/account)

Return only valid JSON with these keys. If any field cannot be extracted, set it to null."""

        return prompt

    def _parse_ai_response(self, response) -> dict:
        """Parse AI response and extract JSON.

        Args:
            response: OpenAI API response.

        Returns:
            Extracted data dictionary.
        """
        import json

        content = response.choices[0].message.content
        data = json.loads(content)

        return data

    def _validate_extracted_data(self, data: dict) -> bool:
        """Validate extracted data has required fields with correct types.

        Args:
            data: Extracted data dictionary.

        Returns:
            True if valid, False otherwise.
        """
        required_fields = ["amount", "merchant", "transaction_date", "transaction_type"]

        # Check required fields exist
        for field in required_fields:
            if field not in data or data[field] is None:
                return False

        # Validate amount is numeric
        try:
            float(data["amount"])
        except (ValueError, TypeError):
            return False

        # Validate transaction_type
        if data["transaction_type"] not in ["debit", "credit"]:
            return False

        # Validate date format
        try:
            datetime.strptime(data["transaction_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            return False

        # Validate merchant is not empty
        if not data["merchant"] or not isinstance(data["merchant"], str):
            return False

        return True

    def _create_draft(self, email: dict, extracted_data: dict) -> TransactionDraft:
        """Create TransactionDraft from extracted data.

        Args:
            email: Original email dictionary.
            extracted_data: Data extracted by AI.

        Returns:
            TransactionDraft object.
        """
        draft = TransactionDraft()

        draft.amount = Decimal(str(abs(extracted_data["amount"])))
        draft.merchant = extracted_data["merchant"]
        draft.transaction_date = datetime.strptime(
            extracted_data["transaction_date"], "%Y-%m-%d"
        )
        draft.transaction_type = extracted_data["transaction_type"]
        draft.reference_number = extracted_data.get("reference_number")
        draft.account_identifier = extracted_data.get("account_identifier")
        draft.gmail_id = email.get("gmail_id")
        draft.subject = email.get("subject")

        return draft
