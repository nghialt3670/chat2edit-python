from typing import Any, Dict, Iterable, List, Optional, Tuple

import google.generativeai as genai
from google.generativeai import GenerationConfig

from chat2edit.prompting.llms.llm import Llm
from chat2edit.prompting.llms.llm_message import LlmMessage

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

    async def generate(
        self, prompt: LlmMessage, history: List[Tuple[LlmMessage, LlmMessage]]
    ) -> List[LlmMessage]:
        input_history = self._create_input_history(history)
        chat_session = self._model.start_chat(history=input_history)
        response = await chat_session.send_message_async(prompt.text)
        return [LlmMessage(text=response.text)]

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": self._model.model_name,
            "system_instruction": self._model.system_instruction,
            "stop_sequences": self._generation_config.stop_sequences,
            "max_out_tokens": self._generation_config.max_output_tokens,
            "temperature": self._generation_config.temperature,
            "top_p": self._generation_config.top_p,
            "top_k": self._generation_config.top_k,
        }

    def _create_input_history(
        self, history: List[Tuple[LlmMessage, LlmMessage]]
    ) -> List[Dict[str, str]]:
        history = []

        for p, a in history:
            history.append({"role": "user", "parts": p.text})
            history.append({"role": "model", "parts": a.text})

        return history
