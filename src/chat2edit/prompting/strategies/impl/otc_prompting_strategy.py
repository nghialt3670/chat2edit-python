import re
from typing import Any, Dict, List, Tuple

from chat2edit.execution.feedbacks import (
    EmptyListParametersFeedback,
    IgnoredReturnValueFeedback,
    IncompleteCycleFeedback,
    InvalidParameterTypeFeedback,
    MismatchListParametersFeedback,
    MissingAllOptionalParametersFeedback,
    ModifiedAttachmentFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.models import (
    ChatCycle,
    ContextualizedFeedback,
    ContextualizedMessage,
    Exemplar,
    LlmMessage,
)
from chat2edit.prompting.strategies.prompting_strategy import PromptingStrategy
from chat2edit.prompting.stubbing.stubs import CodeStub

OTC_PROMPT_TEMPLATE = """
Analyze the following context code:

```python
{context_code}
```

Refer to these exemplary observation-thinking-commands sequences:

{exemplary_otc_sequences}

Now, provide the next thinking and commands for the given sequences.  
Guidelines:  
- Only use the provided context code. 
- Avoid using indentation (e.g., no if, while, with, try, catch, etc.).  
- Do not reuse variable names. 

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
FUNCTION_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE = """
Unexpected error occurred in function `{function}`:
{message}
""".strip()
GLOBAL_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE = """
Unexpected error occurred:
{message}
""".strip()
INCOMPLETE_CYCLE_FEEDBACK_TEXT = "The commands executed successfully. Please continue."
EMPTY_LIST_PARAMETERS_FEEDBACK_TEXT_TEMPLATE = (
    "In function `{function}`, the following parameters are empty: {params_str}."
)
MISMATCH_LIST_PARAMETERS_FEEDBACK_TEXT_TEMPLATE = (
    "In function `{function}`, parameter lengths do not match: {params_str}."
)
MISSING_ALL_OPTIONAL_PARAMETERS_FEEDBACK_TEXT_TEMPLATE = (
    "In function `{function}`, all optional parameters are missing: {params_str}."
)


class OtcPromptingStrategy(PromptingStrategy):
    def create_prompt(
        self,
        cycles: List[ChatCycle],
        exemplars: List[Exemplar],
        context: Dict[str, Any],
    ) -> LlmMessage:
        prompting_context = self.filter_context(context)
        context_code = self.create_context_code(prompting_context)

        exemplary_otc_sequences = "\n\n".join(
            f"Exemplar {idx + 1}:\n{''.join(self.create_otc_sequence(cycle) for cycle in exemplar.cycles)}"
            for idx, exemplar in enumerate(exemplars)
        )

        current_otc_sequences = "\n".join(map(self.create_otc_sequence, cycles))

        return LlmMessage(
            text=OTC_PROMPT_TEMPLATE.format(
                context_code=context_code,
                exemplary_otc_sequences=exemplary_otc_sequences,
                current_otc_sequences=current_otc_sequences,
            )
        )

    def get_refine_prompt(self) -> LlmMessage:
        return LlmMessage(text=OTC_REFINE_PROMPT)

    def extract_code(self, text: str) -> str:
        try:
            _, code = self.extract_thinking_commands(text)
            return code
        except:
            return None

    def filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return context

    def create_context_code(self, context: Dict[str, Any]) -> str:
        code_stub = CodeStub.from_context(context)
        return code_stub.generate()

    def create_otc_sequence(self, cycle: ChatCycle) -> str:
        sequences = []
        observation = self.create_observation_from_request(cycle.request)

        for prompt_cycle in cycle.cycles:
            if not prompt_cycle.exchanges or not prompt_cycle.exchanges[-1].answers:
                continue

            answer = prompt_cycle.exchanges[-1].answers[0]
            thinking, _ = self.extract_thinking_commands(answer.text)

            executed_blocks = list(filter(
                lambda block: block.is_executed, prompt_cycle.blocks
            ))
            commands = "\n".join(
                map(lambda block: block.generated_code, executed_blocks)
            )

            sequences.append(
                COMPLETE_OTC_SEQUENCE_TEMPLATE.format(
                    observation=observation, thinking=thinking, commands=commands
                )
            )

            last_executed_block = executed_blocks[-1]
            if last_executed_block.feedback:
                observation = self.create_observation_from_feedback(
                    last_executed_block.feedback
                )

        if not prompt_cycle.blocks or not prompt_cycle.blocks[-1].response:
            sequences.append(
                INCOMPLETE_OTC_SEQUENCE_TEMPLATE.format(observation=observation)
            )

        return "\n".join(sequences)

    def create_observation_from_request(self, request: ContextualizedMessage) -> str:
        if not request.paths:
            return REQUEST_OBSERVATION_TEMPLATE.format(text=request.text)

        return REQUEST_OBSERVATION_WITH_ATTACHMENTS_TEMPLATE.format(
            text=request.text, attachments=f'[{", ".join(request.paths)}]'
        )

    def create_observation_from_feedback(self, feedback: ContextualizedFeedback) -> str:
        text = self.create_feedback_text(feedback)

        if not feedback.paths:
            return FEEDBACK_OBSERVATION_TEMPLATE.format(
                severity=feedback.severity, text=text
            )

        return FEEDBACK_OBSERVATION_WITH_ATTACHMENTS_TEMPLATE.format(
            severity=feedback.severity,
            text=text,
            attachments=f'[{", ".join(feedback.paths)}]',
        )

    def create_feedback_text(self, feedback: ContextualizedFeedback) -> str:
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
                    function=feedback.function, message=feedback.error.message
                )
            else:
                return GLOBAL_UNEXPECTED_ERROR_FEEDBACK_TEXT_TEMPLATE.format(
                    message=feedback.error.message
                )

        elif isinstance(feedback, IncompleteCycleFeedback):
            return INCOMPLETE_CYCLE_FEEDBACK_TEXT

        elif isinstance(feedback, EmptyListParametersFeedback):
            params_str = ", ".join(feedback.parameters)
            return EMPTY_LIST_PARAMETERS_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function, params_str=params_str
            )

        elif isinstance(feedback, MismatchListParametersFeedback):
            params_with_lengths = [
                f"{param} (length: {length})"
                for param, length in zip(feedback.parameters, feedback.lengths)
            ]
            params_str = ", ".join(params_with_lengths)
            return MISMATCH_LIST_PARAMETERS_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function, params_str=params_str
            )

        elif isinstance(feedback, MissingAllOptionalParametersFeedback):
            params_str = ", ".join(feedback.parameters)
            return MISSING_ALL_OPTIONAL_PARAMETERS_FEEDBACK_TEXT_TEMPLATE.format(
                function=feedback.function, params_str=params_str
            )

        else:
            raise ValueError(f"Unknown feedback: {feedback}")

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
