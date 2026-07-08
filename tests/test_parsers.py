"""Golden-file tests for bank email parsers."""

import json
from pathlib import Path

import pytest

from backend.parsers.hdfc import HDFCParser
from backend.parsers.registry import ParserRegistry, reset_parser_registry


def load_sample_email(bank: str, index: int) -> dict:
    """Load a sample email from the fixtures directory."""
    email_path = Path(__file__).parent / "fixtures" / "sample_emails" / f"{bank}_{index}.txt"
    with open(email_path) as f:
        content = f.read()
    
    # Parse email into dict format
    lines = content.split("\n")
    email = {"body": content}
    
    for line in lines:
        if line.startswith("From:"):
            email["sender"] = line.replace("From:", "").strip()
        elif line.startswith("Subject:"):
            email["subject"] = line.replace("Subject:", "").strip()
    
    return email


def load_expected_parsed(bank: str, index: int) -> dict:
    """Load expected parsed data from JSON."""
    json_path = Path(__file__).parent / "fixtures" / "expected_parsed" / f"{bank}_{index}.json"
    with open(json_path) as f:
        return json.load(f)


class TestHDFCParser:
    """Test suite for HDFC parser."""
    
    def test_hdfc_1(self):
        """Test HDFC sample email 1."""
        email = load_sample_email("hdfc", 1)
        expected = load_expected_parsed("hdfc", 1)
        
        parser = HDFCParser()
        draft = parser.parse(email)
        
        result = draft.to_dict()
        assert result == expected
    
    def test_hdfc_2(self):
        """Test HDFC sample email 2."""
        email = load_sample_email("hdfc", 2)
        expected = load_expected_parsed("hdfc", 2)
        
        parser = HDFCParser()
        draft = parser.parse(email)
        
        result = draft.to_dict()
        assert result == expected
    
    def test_hdfc_3(self):
        """Test HDFC sample email 3."""
        email = load_sample_email("hdfc", 3)
        expected = load_expected_parsed("hdfc", 3)
        
        parser = HDFCParser()
        draft = parser.parse(email)
        
        result = draft.to_dict()
        assert result == expected


class TestParserRegistry:
    """Test suite for ParserRegistry."""
    
    def setup_method(self):
        """Reset registry before each test."""
        reset_parser_registry()
    
    def test_registry_routes_hdfc_correctly(self):
        """Test that registry routes HDFC emails to HDFCParser."""
        registry = ParserRegistry()
        registry.register(HDFCParser())
        
        email = load_sample_email("hdfc", 1)
        parser = registry.get_parser(email)
        
        assert parser is not None
        assert isinstance(parser, HDFCParser)
