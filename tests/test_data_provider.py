import core.ports.data_provider as dp


def test_llm_provider_not_in_data_provider():
    assert not hasattr(dp, "LLMProvider"), (
        "LLMProvider darf nicht in data_provider.py definiert sein — "
        "gehört nach core/ports/llm_provider.py"
    )
