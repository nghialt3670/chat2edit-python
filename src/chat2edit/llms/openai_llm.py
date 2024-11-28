from typing import Any, Coroutine, Iterable, List, Optional

import openai

from chat2edit.base import Llm


class OpenAILlm(Llm):
    def __init__(
        self,
        model_name: str,
        *,
        system_message: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[Iterable[str]] = None,
        top_p: Optional[int] = None,
    ) -> None:
        self.model_name = model_name
        self.system_message = system_message
        self.stop = stop
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

    def set_api_key(self, api_key: str) -> None:
        openai.api_key = api_key

    async def generate(self, messages: List[str]) -> Coroutine[Any, Any, str]:
        if len(messages) % 2 == 0:
            raise ValueError("Invalid messages")

        input_messages = self._create_input_messages(messages)
        response = await openai.ChatCompletion.acreate(
            messages=input_messages,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stop=self.stop,
            top_p=self.top_p,
        )

        return response.choices[0].message.content

    def _create_input_messages(self, messages: List[str]) -> List[str]:
        input_messages = []

        if self.system_message is not None:
            input_messages.append({"role": "system", "content": self.system_message})

        for i, message in enumerate(messages):
            role = "user" if i % 2 == 0 else "assistant"
            input_messages.append({"role": role, "content": message})

        return input_messages
