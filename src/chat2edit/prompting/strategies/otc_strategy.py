from typing import Any, Dict, List, Optional, Tuple

from chat2edit.base import PromptStrategy
from chat2edit.execution.feedbacks import (
    Feedback,
    IgnoredReturnValueFeedback,
    IncompleteCycleFeedback,
    InvalidParameterTypeFeedback,
    ModifiedAttachmentFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.models import ChatCycle, Message
from chat2edit.prompting.stubbing.stubs import CodeStub

OTC_PROMPT_TEMPLATE = """Given this context code:

```
{context_code}
```

Follow these exemplary observation-thinking-commands sequences:

{exemplary_otc_sequences}

Give the next thinking and commands for the current sequence:
Note: Answer in plain text

{current_otc_sequences}"""

OTC_REFINE_PROMPT = """Please answer in this format:

thinking: <YOUR_THINKING>
commands:
```
<YOUR_COMMANDS>
```"""

INVALID_PARAMETER_TYPE_FEEDBACK_TEXT_TEMPLATE = "In function `{function}`, argument for `{parameter}` must be of type `{expected_type}`, but received type `{received_type}`"
MODIFIED_ATTACHMENT_FEEDBACK_TEXT_TEMPLATE = "The variable `{variable}` holds an attachment, which cannot be modified directly. To make changes, create a copy of the object using `deepcopy` and modify the copy instead."
IGNORED_RETURN_VALUE_FEEDBACK_TEXT_TEMPLATE = "The function `{function}` returns a value of type `{value_type}`, but it is not utilized in the code."
FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE = (
    "Unexpected error occurred in function `{func_name}`."
)
GLOBAL_UNEXPECTED_ERROR_FEEDBACK_TEXT = "Unexpected error occurred."
INCOMPLETE_CYCLE_FEEDBACK_TEXT = "The commands executed successfully. Please continue."


class OtcStrategy(PromptStrategy):
    def create_prompt(
        self,
        cycles: List[ChatCycle],
        exemplars: List[ChatCycle],
        context: Dict[str, Any],
    ) -> str:
        context_code = self.create_context_code(context)
        exemplary_otc_sequences = "\n\n".join(
            f"Exemplar {idx + 1}:\n{self.create_otc_sequence(cycle)}"
            for idx, cycle in enumerate(exemplars)
        )

        current_otc_sequences = "\n".join(map(self.create_otc_sequence, cycles))

        return OTC_PROMPT_TEMPLATE.format(
            context_code=context_code,
            exemplary_otc_sequences=exemplary_otc_sequences,
            current_otc_sequences=current_otc_sequences,
        )

    def get_refine_prompt(self) -> str:
        return OTC_REFINE_PROMPT

    def extract_code(self, text: str) -> Optional[str]:
        _, code = self.extract_thinking_commands(text)
        return code

    def create_context_code(self, context: Dict[str, Any]) -> str:
        code_stub = CodeStub.from_context(context)
        return code_stub.generate()

    def create_otc_sequence(self, cycle: ChatCycle) -> str:
        otc_sequence = ""

        request_obs = self.create_observation_from_request(cycle.request)
        otc_sequence += f"observation: {request_obs}\n"

        if cycle.loops:
            for loop in cycle.loops:
                if not loop.answers:
                    continue

                thinking, _ = self.extract_thinking_commands(loop.answers[-1])
                commands = "\n".join(loop.blocks)

                otc_sequence += f"thinking: {thinking}\n"
                otc_sequence += f"commands:\n```\n{commands}\n```\n"

                if loop.feedback:
                    feedback_obs = self.create_observation_from_feedback(loop.feedback)
                    otc_sequence += f"observation: {feedback_obs}\n"
        else:
            otc_sequence += "thinking: ...\n"
            otc_sequence += "commands:\n```\n...\n```"

        return otc_sequence

    def create_observation_from_request(self, request: Message) -> str:
        if not request.attachments:
            return f'user_message("{request.text}")'

        attachments_repr = ", ".join(request.attachments)
        return f'user_message("{request.text}", attachments=[{attachments_repr}])'

    def create_observation_from_feedback(self, feedback: Feedback) -> str:
        text: str = ""

        if isinstance(feedback, InvalidParameterTypeFeedback):
            text = INVALID_PARAMETER_TYPE_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function,
                parameter=feedback.parameter,
                expected_type=feedback.expected_type,
                received_type=feedback.received_type,
            )

        elif isinstance(feedback, ModifiedAttachmentFeedback):
            text = MODIFIED_ATTACHMENT_FEEDBACK_TEXT_TEMPLATE.format(
                variable=feedback.variable
            )

        elif isinstance(feedback, IgnoredReturnValueFeedback):
            text = IGNORED_RETURN_VALUE_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function, value_type=feedback.value_type
            )

        elif isinstance(feedback, UnexpectedErrorFeedback):
            if feedback.function:
                text = FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE.format(
                    function=feedback.function
                )
            else:
                text = GLOBAL_UNEXPECTED_ERROR_FEEDBACK_TEXT

        elif isinstance(feedback, IncompleteCycleFeedback):
            text = INCOMPLETE_CYCLE_FEEDBACK_TEXT

        else:
            raise ValueError(f"Unknown feedback: {feedback}")

        if not feedback.attachments:
            return f'system_{feedback.severity}("{text}")'

        attachments_repr = ", ".join(feedback.attachments)
        return f'system_{feedback.severity}("{text}", attachments=[{attachments_repr}])'

    def extract_thinking_commands(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        parts = [
            part.strip()
            for part in text.replace("observation:", "$")
            .replace("thinking:", "$")
            .replace("commands:", "$")
            .split("$")
            if part.strip()
        ]

        thinking = parts[-2] if len(parts) >= 2 else None
        commands = parts[-1].replace("```", "") if len(parts) >= 2 else None

        return thinking, commands
