from typing import Optional

from app.parsers.base import BaseParser
from app.parsers.mbank import MbankPdfParser
from app.parsers.bakai import BakaiBankParser

# Registry of available parsers
PARSERS = {
    "mbank_pdf": MbankPdfParser,
    "bakai_pdf": BakaiBankParser,
    "bakai_excel": BakaiBankParser,
}


def get_parser(parser_type: str) -> Optional[BaseParser]:
    """Get parser instance by type identifier."""
    parser_class = PARSERS.get(parser_type)
    if parser_class:
        return parser_class()
    return None


__all__ = [
    "BaseParser",
    "MbankPdfParser",
    "BakaiBankParser",
    "get_parser",
]
