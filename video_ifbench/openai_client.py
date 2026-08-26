from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Mapping, Optional

import requests


def raise_for_status_with_body(response: requests.Response) -> None:
    if response.ok:
        return
    body = response.text.strip()
    if len(body) > 2000:
        body = body[:2000] + "...<truncated>"
    message = f"{response.status_code} {response.reason} for url: {response.url}"
    if body:
        message = f"{message}; response body: {body}"
    raise requests.HTTPError(message, response=response)


class OpenAICompatibleClient:
    """Small OpenAI-compatible /chat/completions client.

    The public release intentionally depends only on standard OpenAI-compatible
    chat-completions semantics so users can point it at OpenAI, vLLM, SGLang,
    or other compatible endpoints.
    """

    def __init__(
        self,
        *,
        api_base: str,
        model: str,
        api_key: Optional[str] = None,
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 120.0,
        temperature: float = 0.0,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        chat_template_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.api_key = api_key if api_key is not None else os.environ.get(api_key_env, "")
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.chat_template_kwargs = dict(chat_template_kwargs or {})

    def chat(self, messages: List[Dict[str, Any]], *, response_format: Optional[Dict[str, Any]] = None) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.top_p is not None:
            payload["top_p"] = self.top_p
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.chat_template_kwargs:
            payload["chat_template_kwargs"] = self.chat_template_kwargs
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = requests.post(f"{self.api_base}/chat/completions", headers=headers, json=payload, timeout=self.timeout)
        raise_for_status_with_body(response)
        data = response.json()
        return str(data["choices"][0]["message"].get("content") or "")

    def runtime_meta(self) -> Dict[str, Any]:
        meta = {"api_base": self.api_base, "model": self.model}
        if self.chat_template_kwargs:
            meta["chat_template_kwargs"] = self.chat_template_kwargs
        return meta


def extract_json_object(text: str) -> Any:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        pass
    for open_char, close_char in (("{", "}"), ("[", "]")):
        start = raw.find(open_char)
        if start < 0:
            continue
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(raw)):
            ch = raw[index]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return json.loads(raw[start:index+1])
    raise ValueError("No JSON object or array found in model output.")
