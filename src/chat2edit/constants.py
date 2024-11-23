PYDANTIC_MODEL_STUB_EXCLUDES = {
    "copy",
    "dict",
    "json",
    "model_copy",
    "model_dump",
    "model_dump_json",
    "model_post_init",
    "wrapped_model_post_init",
}

SYSTEM_FILE_STORAGE_FOR_RESPONSE_FILES_SAVE_DIR = "./response_files"
SYSTEM_FILE_STORAGE_FOR_CONTEXT_FILES_SAVE_DIR = "./context_files"

FILE_SRC_TO_PATHS_KEY = "__file_src_to_obj_id__"
OBJ_ID_TO_VARNAME_KEY = "__obj_id_to_varnames__"

EXECUTION_FEEDBACK_SIGNAL_KEY = "__chat2edit_feedback__"
EXECUTION_RESPONSE_SIGNAL_KEY = "__chat2edit_response__"

MAX_VARNAME_SEARCH_INDEX = 100

FILE_OBJECT_MODIFIABLE_ATTRS = {"id", "original", "basename", "filename"}

EXECUTION_CONTEXT_FILE_EXTENSION = ".pkl"
EXECUTION_CONTEXT_FILE_MIME_TYPE = "application/octet-stream"

CLASS_OR_FUNCTION_STUB_KEY = "__stub__"
MODULE_NAME = "chat2edit"
