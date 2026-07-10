def test_public_api_exports_agent_types():
    from hwpx_genai_template_agent import (
        Config,
        DataGenerator,
        GenerationResult,
        HwpxProcessor,
        TemplateMetadata,
        TemplateRetriever,
    )

    assert Config.__name__ == "Config"
    assert HwpxProcessor.__name__ == "HwpxProcessor"
    assert TemplateRetriever.__name__ == "TemplateRetriever"
    assert DataGenerator.__name__ == "DataGenerator"
    assert TemplateMetadata.__name__ == "TemplateMetadata"
    assert GenerationResult.__name__ == "GenerationResult"
