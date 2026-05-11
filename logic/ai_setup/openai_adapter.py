"""
Simple OpenAI adapter to provide chat completions for the wizard when
`OPENAI_API_KEY` is available. This is a lightweight shim so the wizard can
use OpenAI models as an alternative to Anthropic.

The adapter returns a normalized response object with a `content` list of
blocks where each block is either {'text': <string>} or a tool-use like
{'type': 'tool_use', 'id': ..., 'name': ..., 'input': ...} (tool_use is
currently not produced by this adapter, but kept for compatibility).
"""
from typing import List, Dict, Any, Optional
import os


def chat_completion(messages: List[Dict[str, str]], model: str = "gpt-4o-mini",
                    max_tokens: int = 2048, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Call OpenAI ChatCompletion and return a normalized response dict.

    Args:
        messages: list of messages in OpenAI format [{'role': 'user', 'content': '...'}, ...]
        model: model name to use
        max_tokens: max tokens to request
        api_key: optional API key (falls back to environment OPENAI_API_KEY)

    Returns:
        dict with key 'content' -> list of blocks like [{'text': '...'}]
    """
    try:
        import openai
    except Exception:
        raise ImportError("openai package required. Install with: pip install openai")

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Support both modern (OpenAI>=1.x) and legacy clients.
    texts: List[str] = []
    resp = None
    formatted_messages = [{"role": m.get("role", "user"), "content": m.get("content")} for m in messages]

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            max_tokens=max_tokens,
        )
        for ch in getattr(resp, 'choices', []) or []:
            msg = getattr(ch, 'message', None)
            if msg and getattr(msg, 'content', None):
                texts.append(msg.content)
    except Exception:
        # Legacy fallback
        openai.api_key = key
        resp = openai.ChatCompletion.create(
            model=model,
            messages=formatted_messages,
            max_tokens=max_tokens,
        )
        choices = resp.get("choices", [])
        for ch in choices:
            if 'message' in ch and ch['message'] and 'content' in ch['message']:
                texts.append(ch['message']['content'])
            elif 'text' in ch:
                texts.append(ch['text'])

    # Build normalized response
    content_blocks: List[Dict[str, Any]] = []
    for t in texts:
        content_blocks.append({"text": t})

    return {"content": content_blocks, "raw": resp}
