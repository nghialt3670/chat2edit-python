from typing import Iterable, List, Optional

import google.generativeai as genai
from google.generativeai import GenerationConfig

from chat2edit.base import Llm

SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]


class GoogleLlm(Llm):
    def __init__(
        self,
        model_name: str,
        *,
        system_instruction: Optional[str] = None,
        stop_sequences: Optional[Iterable[str]] = None,
        max_out_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> None:
        self._generation_config = GenerationConfig(
            stop_sequences=stop_sequences,
            max_output_tokens=max_out_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )
        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self._generation_config,
            system_instruction=system_instruction,
        )

    def set_api_key(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

    async def generate(self, messages: List[str]) -> str:
        if len(messages) % 2 == 0:
            raise ValueError("Invalid messages")

        history = self._create_input_history(messages[:-1])
        chat_session = self._model.start_chat(history=history)
        response = await chat_session.send_message_async(messages[-1])

        return response.text

    def _create_input_history(self, prev_messages: List[str]) -> List[str]:
        history = []

        for i, message in enumerate(prev_messages):
            role = "user" if i % 2 == 0 else "model"
            history.append({"role": role, "parts": message})

        return history
