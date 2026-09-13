from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.api.main import app

client = TestClient(app)


def test_general_chat_success():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Binary search is an efficient O(log n) algorithm for finding an item in a sorted list.",
        usage_metadata={"input_tokens": 20, "output_tokens": 15, "total_tokens": 35}
    )

    with patch("app.core.llm.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/v1/chat/general",
            json={"question": "What is binary search?"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "Binary search is an efficient" in data["answer"]
    assert data["token_usage"]["total_tokens"] == 35


def test_general_chat_empty_question_validation():
    response = client.post(
        "/api/v1/chat/general",
        json={"question": "   "}
    )
    assert response.status_code == 400
    assert "Question cannot be empty" in response.json()["detail"]


def test_general_chat_api_failure_handled_gracefully():
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API_KEY_INVALID: API key not valid")

    with patch("app.core.llm.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/v1/chat/general",
            json={"question": "Explain React hooks"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "Alex couldn't generate an answer right now" in data["answer"]
    assert "Gemini API key" in data["answer"]
