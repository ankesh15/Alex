from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings


def get_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
        request_timeout=60.0,
        max_retries=2
    )


def parse_llm_response(response) -> tuple[str, dict]:
    """
    Extracts purely clean text string and exact Token usage metadata.
    """
    if response is None:
        return "", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # 1. Clean Text Extraction (Ignore extras/signatures)
    clean_text = ""
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, str):
            clean_text = content
        elif isinstance(content, list):
            text_blocks = []
            for item in content:
                if isinstance(item, str):
                    text_blocks.append(item)
                elif isinstance(item, dict):
                    if "text" in item and item["text"]:
                        text_blocks.append(str(item["text"]))
                    elif "content" in item and item["content"]:
                        text_blocks.append(str(item["content"]))
                elif hasattr(item, "text"):
                    text_blocks.append(str(item.text))
            clean_text = "\n".join(text_blocks)
        elif isinstance(content, dict):
            clean_text = content.get("text", str(content))
        else:
            clean_text = str(content)
    else:
        clean_text = str(response)

    # Clean any leftover trailing brackets or dict artifacts
    clean_text = clean_text.strip()

    # 2. Universal Token Usage Extraction
    token_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    # LangChain usage_metadata check
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        if isinstance(um, dict):
            token_usage["prompt_tokens"] = um.get("input_tokens", 0) or 0
            token_usage["completion_tokens"] = um.get("output_tokens", 0) or 0
            token_usage["total_tokens"] = um.get("total_tokens", 0) or 0
        elif hasattr(um, "input_tokens"):
            token_usage["prompt_tokens"] = getattr(um, "input_tokens", 0) or 0
            token_usage["completion_tokens"] = getattr(um, "output_tokens", 0) or 0
            token_usage["total_tokens"] = getattr(um, "total_tokens", 0) or 0

    # Fallback to response_metadata
    elif hasattr(response, "response_metadata") and response.response_metadata:
        rm = response.response_metadata
        if isinstance(rm, dict):
            usage = rm.get("token_usage", {}) or rm.get("usage", {})
            if isinstance(usage, dict):
                p_tok = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
                c_tok = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
                t_tok = usage.get("total_tokens", p_tok + c_tok) or (p_tok + c_tok)
                token_usage["prompt_tokens"] = p_tok
                token_usage["completion_tokens"] = c_tok
                token_usage["total_tokens"] = t_tok

    return clean_text, token_usage
