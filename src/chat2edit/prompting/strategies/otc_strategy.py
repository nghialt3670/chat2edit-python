import re
from typing import Any, Dict, List, Tuple

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

OTC_PROMPT_TEMPLATE = """
Given this context code:

```python
{context_code}
```

Follow these exemplary observation-thinking-commands sequences:

{exemplary_otc_sequences}

Give the next thinking and commands for the current sequences:

{current_otc_sequences}
""".strip()

REQUEST_OBSERVATION_TEMPLATE = 'user_message("{text}")'
REQUEST_OBSERVATION_WITH_ATTACHMENTS_TEMPLATE = (
    'user_message("{text}", attachments={attachments})'
)

FEEDBACK_OBSERVATION_TEMPLATE = 'system_{severity}("{text}")'
FEEDBACK_OBSERVATION_WITH_ATTACHMENTS_TEMPLATE = (
    'system_{severity}("{text}", attachments={attachments})'
)

COMPLETE_OTC_SEQUENCE_TEMPLATE = """
observation: {observation}
thinking: {thinking}
commands:
```python
{commands}
```
""".strip()

INCOMPLETE_OTC_SEQUENCE_TEMPLATE = """
observation: {observation}
""".strip()

OTC_REFINE_PROMPT = """
Please answer in this format:

thinking: <YOUR_THINKING>
commands:
```python
<YOUR_COMMANDS>
```
""".strip()

INVALID_PARAMETER_TYPE_FEEDBACK_TEXT_TEMPLATE = "In function `{function}`, argument for `{parameter}` must be of type `{expected_type}`, but received type `{received_type}`"
MODIFIED_ATTACHMENT_FEEDBACK_TEXT_TEMPLATE = "The variable `{variable}` holds an attachment, which cannot be modified directly. To make changes, create a copy of the object using `deepcopy` and modify the copy instead."
IGNORED_RETURN_VALUE_FEEDBACK_TEXT_TEMPLATE = "The function `{function}` returns a value of type `{value_type}`, but it is not utilized in the code."
FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE = (
    "Unexpected error occurred in function `{function}`."
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
            f"Exemplar {idx + 1}:\n{self.create_otc_sequences(cycle)}"
            for idx, cycle in enumerate(exemplars)
        )
        current_otc_sequences = "\n".join(map(self.create_otc_sequences, cycles))

        return OTC_PROMPT_TEMPLATE.format(
            context_code=context_code,
            exemplary_otc_sequences=exemplary_otc_sequences,
            current_otc_sequences=current_otc_sequences,
        )

    def get_refine_prompt(self) -> str:
        return OTC_REFINE_PROMPT

    def extract_code(self, text: str) -> str:
        _, code = self.extract_thinking_commands(text)
        return code

    def create_context_code(self, context: Dict[str, Any]) -> str:
        code_stub = CodeStub.from_context(context)
        return code_stub.generate()

    def create_otc_sequences(self, cycle: ChatCycle) -> str:
        sequences = []
        observation = self.create_observation_from_request(cycle.request)

        for loop in cycle.loops:
            if not loop.answers:
                continue

            thinking, _ = self.extract_thinking_commands(loop.answers[-1])
            commands = "\n".join(loop.blocks)

            sequences.append(
                COMPLETE_OTC_SEQUENCE_TEMPLATE.format(
                    observation=observation, thinking=thinking, commands=commands
                )
            )

            if loop.feedback:
                observation = self.create_observation_from_feedback(loop.feedback)

        if not cycle.response:
            sequences.append(
                INCOMPLETE_OTC_SEQUENCE_TEMPLATE.format(observation=observation)
            )

        return "\n".join(sequences)

    def create_observation_from_request(self, request: Message) -> str:
        if not request.attachments:
            return REQUEST_OBSERVATION_TEMPLATE.format(text=request.text)

        return REQUEST_OBSERVATION_WITH_ATTACHMENTS_TEMPLATE.format(
            text=request.text, attachments=f'[{", ".join(request.attachments)}]'
        )

    def create_feedback_text(self, feedback: Feedback) -> str:
        if isinstance(feedback, InvalidParameterTypeFeedback):
            return INVALID_PARAMETER_TYPE_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function,
                parameter=feedback.parameter,
                expected_type=feedback.expected_type,
                received_type=feedback.received_type,
            )

        elif isinstance(feedback, ModifiedAttachmentFeedback):
            return MODIFIED_ATTACHMENT_FEEDBACK_TEXT_TEMPLATE.format(
                variable=feedback.variable
            )

        elif isinstance(feedback, IgnoredReturnValueFeedback):
            return IGNORED_RETURN_VALUE_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function, value_type=feedback.value_type
            )

        elif isinstance(feedback, UnexpectedErrorFeedback):
            if feedback.function:
                return FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE.format(
                    function=feedback.function
                )
            else:
                return GLOBAL_UNEXPECTED_ERROR_FEEDBACK_TEXT

        elif isinstance(feedback, IncompleteCycleFeedback):
            return INCOMPLETE_CYCLE_FEEDBACK_TEXT

        else:
            raise ValueError(f"Unknown feedback: {feedback}")

    def create_observation_from_feedback(self, feedback: Feedback) -> str:
        text = self.create_feedback_text(feedback)

        if not feedback.attachments:
            return FEEDBACK_OBSERVATION_TEMPLATE.format(
                severity=feedback.severity, text=text
            )

        return FEEDBACK_OBSERVATION_WITH_ATTACHMENTS_TEMPLATE.format(
            severity=feedback.severity,
            text=text,
            attachments=f'[{", ".join(feedback.attachments)}]',
        )

    def extract_thinking_commands(self, text: str) -> Tuple[str, str]:
        parts = [
            part.strip()
            for part in text.replace("observation:", "$")
            .replace("thinking:", "$")
            .replace("commands:", "$")
            .split("$")
            if part.strip()
        ]

        thinking = parts[-2]
        commands = (
            re.search(r"```python(.*?)```", parts[-1], re.DOTALL).group(1).strip()
        )

        return thinking, commands
