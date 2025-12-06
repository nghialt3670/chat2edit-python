import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

import openai

from chat2edit.models import LlmMessage
from chat2edit.prompting.llms.llm import Llm


class OpenAILlm(Llm):
    def __init__(
        self,
        model: str,
        *,
        system_message: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[Iterable[str]] = None,
        top_p: Optional[int] = None,
    ) -> None:
        self._model = model
        self._system_message = system_message
        self._stop = stop
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._top_p = top_p
        self.set_api_key(os.getenv("OPENAI_API_KEY"))

    def set_api_key(self, api_key: str) -> None:
        openai.api_key = api_key

    async def generate(
        self, prompt: LlmMessage, history: List[Tuple[LlmMessage, LlmMessage]]
    ) -> LlmMessage:
        response = await openai.ChatCompletion.acreate(
            messages=self._create_messages(prompt, history),
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            stop=self._stop,
            top_p=self._top_p,
        )

        return LlmMessage(text=response.choices[0].message.content)

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": self._model,
            "system_message": self._system_message,
            "stop": self._stop,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "top_p": self._top_p,
        }

    def _create_messages(
        self, prompt: LlmMessage, history: List[Tuple[LlmMessage, LlmMessage]]
    ) -> List[Dict[str, str]]:
        messages = []

        if self._system_message is not None:
            messages.append({"role": "system", "content": self._system_message})

        for p, a in history:
            messages.append({"role": "user", "content": p.text})
            messages.append({"role": "assistant", "content": a.text})

        messages.append({"role": "user", "content": prompt.text})
        return messages
