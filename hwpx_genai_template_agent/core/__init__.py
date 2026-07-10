__all__ = ["DataGenerator", "HwpxProcessor", "TemplateRetriever"]


def __getattr__(name: str):
    if name == "HwpxProcessor":
        from .hwpx_processor import HwpxProcessor

        return HwpxProcessor
    if name == "DataGenerator":
        from .llm_agent import DataGenerator

        return DataGenerator
    if name == "TemplateRetriever":
        from .vector_store import TemplateRetriever

        return TemplateRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
