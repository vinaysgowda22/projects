"""Parser registry for auto-selecting the appropriate bank parser."""

from typing import Optional

from loguru import logger

from backend.parsers.base import BaseParser, TransactionDraft


class ParserRegistry:
    """Registry for bank email parsers with auto-selection logic."""
    
    def __init__(self):
        """Initialize an empty parser registry."""
        self._parsers: list[BaseParser] = []
    
    def register(self, parser: BaseParser) -> None:
        """Register a parser with the registry.
        
        Args:
            parser: Instance of a BaseParser subclass.
        """
        self._parsers.append(parser)
        logger.info(f"Registered parser: {parser.__class__.__name__}")
    
    def get_parser(self, email: dict) -> Optional[BaseParser]:
        """Get the appropriate parser for an email.
        
        Args:
            email: Dictionary containing email data with 'sender' and 'subject' keys.
        
        Returns:
            The first parser that can handle the email, or None if no match.
        """
        sender = email.get("sender", "").lower()
        subject = email.get("subject", "").lower()
        
        for parser in self._parsers:
            if parser.can_parse(email):
                logger.debug(f"Selected parser {parser.__class__.__name__} for email from {sender}")
                return parser
        
        logger.warning(f"No parser found for email from {sender} with subject: {subject}")
        return None
    
    def parse(self, email: dict) -> TransactionDraft:
        """Parse an email using the appropriate parser.
        
        Args:
            email: Dictionary containing email data.
        
        Returns:
            TransactionDraft with extracted data.
        
        Raises:
            ValueError: If no parser can handle the email.
        """
        parser = self.get_parser(email)
        if parser is None:
            raise ValueError(f"No parser found for email from {email.get('sender')}")
        
        return parser.parse(email)
    
    def list_parsers(self) -> list[str]:
        """List all registered parser class names."""
        return [parser.__class__.__name__ for parser in self._parsers]


def create_default_registry() -> ParserRegistry:
    """Create a registry pre-populated with all available bank parsers.

    Regex-based bank parsers are always registered. The AI fallback parser is
    only registered when AI features are enabled in the configuration.

    Returns:
        A ParserRegistry with the default set of parsers registered.
    """
    # Imported here to avoid circular imports at module load time.
    from backend.config import get_config
    from backend.parsers.amex import AmexParser
    from backend.parsers.axis import AxisParser
    from backend.parsers.hdfc import HDFCParser
    from backend.parsers.icici import ICICIParser
    from backend.parsers.kotak import KotakParser
    from backend.parsers.sbi import SBIParser

    registry = ParserRegistry()
    for parser_cls in (
        HDFCParser,
        ICICIParser,
        AxisParser,
        SBIParser,
        AmexParser,
        KotakParser,
    ):
        registry.register(parser_cls())

    if get_config().ai.enabled:
        from backend.parsers.ai_parser import AIParser

        registry.register(AIParser())

    return registry


# Global registry instance
_registry: Optional[ParserRegistry] = None


def get_parser_registry() -> ParserRegistry:
    """Get the global parser registry instance (singleton pattern)."""
    global _registry
    if _registry is None:
        _registry = create_default_registry()
    return _registry


def reset_parser_registry() -> None:
    """Reset the global parser registry (useful for testing)."""
    global _registry
    _registry = None
