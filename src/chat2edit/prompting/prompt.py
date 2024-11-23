import traceback
from typing import List

from chat2edit.base.llm import Llm
from chat2edit.base.prompt_strategy import PromptStrategy
from chat2edit.models.context import Context
from chat2edit.models.cycles import ChatCycle, PromptingResult
from chat2edit.models.error import Error


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
            result.error = Error(message=str(e), stack_trace=traceback.format_exc())
            break

        result.messages.append(answer)
        result.code = strategy.extract_code(answer)

        if result.code:
            break

        refine_prompt = strategy.get_refine_prompt()
        result.messages.append(refine_prompt)

    return result
