from typing import TYPE_CHECKING, Annotated, Literal, Optional, Union

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


class Feedback(Message):
    type: str  # Discriminator field - must be overridden by subclasses
    severity: Literal["info", "warning", "error"]
    function: Optional[str] = Field(default=None)


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
