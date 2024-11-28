PYDANTIC_MODEL_EXCLUDES = {
    "copy",
    "dict",
    "json",
    "model_copy",
    "model_dump",
    "model_dump_json",
    "model_post_init",
    "wrapped_model_post_init",
}


EXECUTION_FEEDBACK_SIGNAL_KEY = "__chat2edit_feedback__"
EXECUTION_RESPONSE_SIGNAL_KEY = "__chat2edit_response__"

MAX_VARNAME_SEARCH_INDEX = 100

FILE_OBJECT_MODIFIABLE_ATTRS = {"id", "original", "basename", "filename"}

EXECUTION_CONTEXT_FILE_EXTENSION = ".pkl"
EXECUTION_CONTEXT_FILE_MIME_TYPE = "application/octet-stream"

CLASS_OR_FUNCTION_STUB_KEY = "__stub__"
MODULE_NAME = "chat2edit"

# signaling
RESPONSE_SIGNAL_KEY = "__response__"
FEEDBACK_SIGNAL_KEY = "__feedback__"

# models
MESSAGE_TEXT_MAX_CHARACTERS = 10000
MESSAGE_MAX_ATTACHMENTS = 100
ATTACHMENT_MAX_ATTRIBUTE_PATHS = 10
ATTACHMENT_MAX_QUERY_OBJECTS = 10
CONTEXT_MAX_EXEMPLARY_CYCLES = 3


NUM_EDIT_CYCLES_PER_CHAT_CYCLE_RANGE = [1, 7]
NUM_CHAT_CYCLES_PER_PROMPT_RANGE = [10, 20]
NUM_PROMPTS_PER_EDIT_CYCLE_RANGE = [1, 3]

CLASS_INFO_EXCLUDES_KEY = "__excludes__"
