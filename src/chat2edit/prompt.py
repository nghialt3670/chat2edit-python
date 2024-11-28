import traceback
from typing import List

from chat2edit.base import Llm, PromptStrategy
from chat2edit.models import ChatCycle, Context, Error, PromptingResult


async def prompt(
    cycles: List[ChatCycle],
    llm: Llm,
    strategy: PromptStrategy,
    context: Context,
    max_prompts: int,
) -> PromptingResult:
    prompt = strategy.create_prompt(cycles, context)
    result = PromptingResult(messages=[prompt])

    while len(result.messages) // 2 < max_prompts:
        try:
            answer = await llm.generate(result.messages)

        except Exception as e:
            result.error = Error.from_exception(e)
            break

        result.messages.append(answer)
        result.code = strategy.extract_code(answer)

        if result.code:
            break

        refine_prompt = strategy.get_refine_prompt()
        result.messages.append(refine_prompt)

    return result
