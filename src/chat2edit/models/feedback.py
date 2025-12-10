from typing import TYPE_CHECKING, Annotated, Dict, Literal, Optional, Type, Union

from pydantic import Field

from chat2edit.models.message import Message

if TYPE_CHECKING:
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

    # Type alias for mypy - defines the union of all feedback types
    FeedbackUnion = Union[
        "EmptyListParametersFeedback",
        "IgnoredReturnValueFeedback",
        "IncompleteCycleFeedback",
        "InvalidParameterTypeFeedback",
        "MismatchListParametersFeedback",
        "MissingAllOptionalParametersFeedback",
        "ModifiedAttachmentFeedback",
        "UnexpectedErrorFeedback",
    ]


# Registry for Feedback subclasses keyed by their 'type' field value
_FEEDBACK_REGISTRY: Dict[str, Type["Feedback"]] = {}


class Feedback(Message):
    type: str  # Discriminator field - must be overridden by subclasses
    severity: Literal["info", "warning", "error"]
    function: Optional[str] = Field(default=None)

    def __init_subclass__(cls, **kwargs):
        """Automatically register Feedback subclasses by their 'type' field value."""
        super().__init_subclass__(**kwargs)
        # Try to get the type value from class annotations or model_fields
        type_value = None
        
        # First, try to get from class annotations (available at definition time)
        if hasattr(cls, "__annotations__") and "type" in cls.__annotations__:
            annotation = cls.__annotations__["type"]
            # Check if it's a Literal type
            if hasattr(annotation, "__args__"):
                args = annotation.__args__
                if args and isinstance(args[0], str):
                    type_value = args[0]
        
        # If not found in annotations, try model_fields (available after Pydantic processes the class)
        if not type_value and hasattr(cls, "model_fields") and "type" in cls.model_fields:
            type_field = cls.model_fields["type"]
            if hasattr(type_field, "default") and type_field.default is not None:
                type_value = type_field.default
            elif hasattr(type_field, "default_factory"):
                type_value = type_field.default_factory()
            elif hasattr(type_field, "annotation"):
                annotation = type_field.annotation
                if hasattr(annotation, "__args__"):
                    args = annotation.__args__
                    if args and isinstance(args[0], str):
                        type_value = args[0]
        
        # Also check if there's a default value set directly on the class
        if not type_value and hasattr(cls, "type"):
            type_attr = getattr(cls, "type", None)
            if isinstance(type_attr, str):
                type_value = type_attr
        
        if isinstance(type_value, str):
            _FEEDBACK_REGISTRY[type_value] = cls


def register_feedback_class(feedback_class: Type[Feedback]) -> None:
    """Manually register a Feedback subclass. Useful for custom feedback classes."""
    if not issubclass(feedback_class, Feedback):
        raise ValueError(f"{feedback_class} must be a subclass of Feedback")
    
    type_value = None
    
    # Try multiple methods to get the type value
    # 1. Check class annotations
    if hasattr(feedback_class, "__annotations__") and "type" in feedback_class.__annotations__:
        annotation = feedback_class.__annotations__["type"]
        if hasattr(annotation, "__args__"):
            args = annotation.__args__
            if args and isinstance(args[0], str):
                type_value = args[0]
    
    # 2. Check model_fields (available after Pydantic processes the class)
    if not type_value and hasattr(feedback_class, "model_fields") and "type" in feedback_class.model_fields:
        type_field = feedback_class.model_fields["type"]
        if hasattr(type_field, "default") and type_field.default is not None:
            type_value = type_field.default
        elif hasattr(type_field, "default_factory"):
            type_value = type_field.default_factory()
        elif hasattr(type_field, "annotation"):
            annotation = type_field.annotation
            if hasattr(annotation, "__args__"):
                args = annotation.__args__
                if args and isinstance(args[0], str):
                    type_value = args[0]
    
    # 3. Check class attribute directly
    if not type_value and hasattr(feedback_class, "type"):
        type_attr = getattr(feedback_class, "type", None)
        if isinstance(type_attr, str):
            type_value = type_attr
    
    # 4. Try creating a temporary instance to get the default value
    if not type_value:
        try:
            # Create instance with minimal required fields to get the type default
            temp_instance = feedback_class(
                type="temp",  # This will be overridden by the default
                severity="info"
            )
            if hasattr(temp_instance, "type"):
                type_value = temp_instance.type
        except Exception:
            pass
    
    if isinstance(type_value, str) and type_value != "temp":
        _FEEDBACK_REGISTRY[type_value] = feedback_class
    else:
        raise ValueError(
            f"Could not determine 'type' value for {feedback_class}. "
            f"Ensure the class has a 'type' field with a Literal annotation and default value."
        )


def get_feedback_class(type_value: str) -> Optional[Type[Feedback]]:
    """Get a Feedback subclass by its type value."""
    return _FEEDBACK_REGISTRY.get(type_value)


# Import all feedback types for the union (at runtime to avoid circular imports)
def _get_feedback_union():
    """
    Creates a discriminated union of all Feedback subclasses.

    When adding a new Feedback subclass:
    1. Ensure it has a unique `type: Literal["your_type"] = "your_type"` field
    2. Import it in chat2edit.execution.feedbacks.__init__.py
    3. Add it to the imports and explicit_feedback_classes list below
    4. The auto-discovery will also pick it up if it's imported before this runs
    """
    # Import all feedback types to ensure they're registered as Feedback subclasses
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

    # Collect explicitly imported feedback classes
    explicit_feedback_classes = [
        EmptyListParametersFeedback,
        IgnoredReturnValueFeedback,
        IncompleteCycleFeedback,
        InvalidParameterTypeFeedback,
        MismatchListParametersFeedback,
        MissingAllOptionalParametersFeedback,
        ModifiedAttachmentFeedback,
        UnexpectedErrorFeedback,
    ]

    # Also include any other Feedback subclasses that might have been imported
    # This makes it extensible - new feedback types will be automatically included
    # as long as they're imported somewhere before this module is used
    all_feedback_classes = set(explicit_feedback_classes)

    def collect_subclasses(cls):
        """Recursively collect all subclasses."""
        for subclass in cls.__subclasses__():
            if subclass is not Feedback and issubclass(subclass, Feedback):
                all_feedback_classes.add(subclass)
                collect_subclasses(subclass)

    collect_subclasses(Feedback)
    
    # Ensure all feedback classes are registered in the registry
    # This is important for parsing feedback from dict/JSON
    for feedback_class in all_feedback_classes:
        # Try to register if not already registered
        # The __init_subclass__ should have registered them, but this ensures it
        if feedback_class not in _FEEDBACK_REGISTRY.values():
            try:
                register_feedback_class(feedback_class)
            except Exception:
                # If registration fails, continue - it might already be registered
                pass

    feedback_classes = list(all_feedback_classes)

    if len(feedback_classes) == 0:
        # Fallback to just Feedback if no subclasses found
        return Annotated[Feedback, Field(discriminator="type")]

    if len(feedback_classes) == 1:
        return Annotated[feedback_classes[0], Field(discriminator="type")]

    return Annotated[
        Union[tuple(feedback_classes)],
        Field(discriminator="type"),
    ]


# Create the discriminated union type for runtime (Pydantic)
# At runtime, this replaces the type alias with the actual discriminated union
# Note: This is computed at module import time, but _get_feedback_union() uses
# collect_subclasses() which will find all Feedback subclasses that have been
# imported at the time it's called. To include custom feedback classes, ensure
# they are imported before any module that uses FeedbackUnion.
if not TYPE_CHECKING:
    # Store the function to allow lazy recomputation if needed
    _get_feedback_union_func = _get_feedback_union
    # Create initial union - this will be recomputed if Feedback subclasses are added later
    FeedbackUnion = _get_feedback_union()  # type: ignore[assignment, misc]
    
    # Provide a way to refresh the union if custom feedback classes are added
    def _refresh_feedback_union():
        """Refresh FeedbackUnion to include newly imported Feedback subclasses."""
        global FeedbackUnion
    FeedbackUnion = _get_feedback_union()  # type: ignore[assignment, misc]
