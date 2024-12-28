from dataclasses import dataclass, field
from itertools import zip_longest
from typing import List, Optional

from chat2edit.base import ContextProvider, Llm, PromptStrategy
from chat2edit.models import ChatCycle, Error


@dataclass
class PromptingResult:
    prompts: List[str] = field(default_factory=list)
    answers: List[str] = field(default_factory=list)
    error: Optional[Error] = field(default=None)
    code: Optional[str] = field(default=None)


async def prompt(
    *,
    cycles: List[ChatCycle],
    llm: Llm,
    provider: ContextProvider,
    strategy: PromptStrategy,
    max_prompts: int,
) -> PromptingResult:
    exemplars = provider.get_exemplars()
    context = provider.get_context()

    result = PromptingResult()

    while not result.code and len(result.prompts) < max_prompts:
        prompt = (
            strategy.get_refine_prompt()
            if result.prompts
            else strategy.create_prompt(cycles, exemplars, context)
        )
        result.prompts.append(prompt)

        try:
            messages = _create_input_messages(result.prompts, result.answers)
            answer = await llm.generate(messages)
            result.answers.append(answer)

        except Exception as e:
            result.error = Error.from_exception(e)
            break

        try:
            result.code = strategy.extract_code(answer)
        except:
            pass

    return result


def _create_input_messages(prompts: List[str], answers: List[str]) -> List[str]:
    return [
        msg for pair in zip_longest(prompts, answers) for msg in pair if msg is not None
    ]
