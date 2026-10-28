from app.config import Settings
from app.llm import ClaudeLLM, GeminiLLM, build_llm


def test_build_llm_selects_provider() -> None:
    claude = build_llm(Settings(llm_provider="anthropic", anthropic_api_key="k"))
    gemini = build_llm(Settings(llm_provider="gemini", gemini_api_key="k"))
    assert isinstance(claude, ClaudeLLM)
    assert isinstance(gemini, GeminiLLM)


def test_llm_configured_follows_provider() -> None:
    assert not Settings(llm_provider="gemini", anthropic_api_key="k").llm_configured
    assert Settings(llm_provider="gemini", gemini_api_key="k").llm_configured
    assert Settings(llm_provider="anthropic", anthropic_api_key="k").llm_configured


def test_gemini_maps_roles() -> None:
    llm = GeminiLLM("k", "m", 10)
    messages = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    contents, config = llm._args("sys", messages)
    assert [c.role for c in contents] == ["user", "model"]
    assert config.system_instruction == "sys"
