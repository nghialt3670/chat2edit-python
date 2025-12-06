import math
from typing import Any, Dict, List

from chat2edit.context.providers.context_provider import ContextProvider
from chat2edit.execution.decorators import respond
from chat2edit.models import (
    ExemplaryChatCycle,
    ChatMessage,
    ExemplaryExecutionBlock,
    Exemplar,
    LlmMessage,
    ExemplaryPromptCycle,
    ExemplaryPromptExchange,
)


@respond
def respond_to_user(text: str, attachments: List[Any] = []) -> None:
    return ChatMessage(text=text, attachments=attachments)


class CalculatorContextProvider(ContextProvider):
    def get_context(self) -> Dict[str, Any]:
        return {
            "math": math,
            "respond_to_user": respond_to_user,
        }

    def get_exemplars(self) -> List[Exemplar]:
        return [
            Exemplar(
                cycles=[
                    ExemplaryChatCycle(
                        request=ChatMessage(
                            text="What is the square root of 1296?",
                        ),
                        cycles=[
                            ExemplaryPromptCycle(
                                exchanges=[
                                    ExemplaryPromptExchange(
                                        answer=LlmMessage(
                                            text="""
thinking: I should use the math module to calculate the square root.
commands:
```python
result = math.sqrt(1296)
respond_to_user(f"The square root of 1296 is {result}")
```
                                            """,
                                        ),
                                    )
                                ],
                                blocks=[
                                    ExemplaryExecutionBlock(
                                        generated_code="result = math.sqrt(1296)",
                                    ),
                                    ExemplaryExecutionBlock(
                                        generated_code='respond_to_user(f"The square root of 1296 is {result}")',
                                        response=ChatMessage(
                                            text="The square root of 1296 is 36.",
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                ]
            ),
            Exemplar(
                cycles=[
                    ExemplaryChatCycle(
                        request=ChatMessage(
                            text="What is the cosine of 57 degrees?",
                        ),
                        cycles=[
                            ExemplaryPromptCycle(
                                exchanges=[
                                    ExemplaryPromptExchange(
                                        answer=LlmMessage(
                                            text="""
thinking: I should use the math module to calculate the cosine.
commands:
```python
radians = math.radians(57)
result = math.cos(radians)
respond_to_user(f"The cosine of 57 degrees is {result}")
```
                                            """
                                        ),
                                    ),
                                ],
                                blocks=[
                                    ExemplaryExecutionBlock(
                                        generated_code="radians = math.radians(57)",
                                    ),
                                    ExemplaryExecutionBlock(
                                        generated_code="result = math.cos(radians)",
                                    ),
                                    ExemplaryExecutionBlock(
                                        generated_code='respond_to_user(f"The cosine of 57 degrees is {result}")',
                                        response=ChatMessage(
                                            text="The cosine of 57 degrees is 0.5446390350150271.",
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ]
            ),
        ]
