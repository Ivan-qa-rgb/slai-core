from __future__ import annotations

import json
import os
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class OllamaError(RuntimeError):
    """Ошибка обращения к локальному Ollama API."""

class OllamaClient:
    """Клиент локального Ollama API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
        think: bool = False,
        num_ctx: int = 4096,
        num_predict: int = 768,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "SLAI_OLLAMA_URL",
                "http://localhost:11434",
            )
        ).rstrip("/")

        self.model = (
            model
            or os.getenv(
                "SLAI_OLLAMA_MODEL",
                "qwen3:1.7b",
            )
        )

        self.timeout = timeout
        self.think = think
        self.num_ctx = num_ctx
        self.num_predict = num_predict

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        json_mode: bool = False,
        think: bool | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = []

        if system:
            messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "think": self.think if think is None else think,
            "options": {
                "temperature": temperature,
                "num_ctx": (
                    self.num_ctx
                    if num_ctx is None
                    else num_ctx
                ),
                "num_predict": (
                    self.num_predict
                    if num_predict is None
                    else num_predict
                ),
            },
        }

        if json_mode:
            payload["format"] = "json"

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        request = Request(
            url=f"{self.base_url}/api/chat",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw_response = response.read()

        except HTTPError as error:
            details = error.read().decode(
                "utf-8",
                errors="replace",
            )
            raise OllamaError(
                f"Ollama HTTP {error.code}: {details}"
            ) from error

        except URLError as error:
            raise OllamaError(
                f"Ollama недоступен: {error.reason}"
            ) from error

        except (TimeoutError, socket.timeout) as error:
            raise OllamaError(
                f"Истёк таймаут Ollama: {self.timeout:.0f} секунд"
            ) from error

        try:
            result = json.loads(
                raw_response.decode("utf-8")
            )

        except json.JSONDecodeError as error:
            raise OllamaError(
                "Ollama вернул некорректный JSON"
            ) from error

        if not isinstance(result, dict):
            raise OllamaError(
                "Ответ Ollama имеет неправильный формат"
            )

        if result.get("error"):
            raise OllamaError(
                str(result["error"])
            )

        message = result.get("message")

        if not isinstance(message, dict):
            raise OllamaError(
                "В ответе Ollama отсутствует message"
            )

        content = message.get("content")

        if not isinstance(content, str):
            raise OllamaError(
                "В ответе Ollama отсутствует message.content"
            )

        return result

    def text(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        json_mode: bool = False,
        think: bool | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
    ) -> str:
        result = self.chat(
            prompt=prompt,
            system=system,
            model=model,
            temperature=temperature,
            json_mode=json_mode,
            think=think,
            num_ctx=num_ctx,
            num_predict=num_predict,
        )

        return result["message"]["content"].strip()
