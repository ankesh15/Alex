from unittest.mock import patch
from langchain_core.messages import AIMessage
from app.core.llm import parse_llm_response, get_llm


def test_parse_llm_response_string():
    msg = AIMessage(
        content="Clean response text",
        usage_metadata={"input_tokens": 12, "output_tokens": 8, "total_tokens": 20}
    )
    text, tokens = parse_llm_response(msg)
    assert text == "Clean response text"
    assert tokens["prompt_tokens"] == 12
    assert tokens["completion_tokens"] == 8
    assert tokens["total_tokens"] == 20


def test_parse_llm_response_list_content():
    msg = AIMessage(content=["Block 1", {"text": "Block 2"}])
    msg.response_metadata = {"token_usage": {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20}}
    text, tokens = parse_llm_response(msg)
    assert "Block 1" in text
    assert "Block 2" in text
    assert tokens["prompt_tokens"] == 15
    assert tokens["completion_tokens"] == 5
    assert tokens["total_tokens"] == 20


def test_parse_llm_response_none():
    text, tokens = parse_llm_response(None)
    assert text == ""
    assert tokens["prompt_tokens"] == 0
    assert tokens["completion_tokens"] == 0
    assert tokens["total_tokens"] == 0


@patch("app.core.llm.settings.GOOGLE_API_KEY", "mock_api_key_for_tests")
def test_get_llm_instantiation():
    llm = get_llm(temperature=0.2)
    assert llm is not None
    assert llm.temperature == 0.2
