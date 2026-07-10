from .config import Config
from .models import GenerationResult, TemplateMetadata

__all__ = [
    "Config",
    "DataGenerator",
    "GenerationResult",
    "HwpxProcessor",
    "TemplateMetadata",
    "TemplateRetriever",
]


def __getattr__(name: str):
    if name == "HwpxProcessor":
        from .core.hwpx_processor import HwpxProcessor

        return HwpxProcessor
    if name == "DataGenerator":
        from .core.llm_agent import DataGenerator

        return DataGenerator
    if name == "TemplateRetriever":
        from .core.vector_store import TemplateRetriever

        return TemplateRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
