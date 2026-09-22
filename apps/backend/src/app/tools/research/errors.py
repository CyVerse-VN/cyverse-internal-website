class ResearchError(Exception):
    status_code = 400
    detail = "The research request could not be completed"
    code = "research_error"


class ResearchSessionNotFoundError(ResearchError):
    status_code = 404
    detail = "Research session not found"
    code = "research_session_not_found"


class ResearchSessionConflictError(ResearchError):
    status_code = 409
    detail = "The research session can no longer be changed"
    code = "research_session_conflict"


class ResearchPipelineError(ResearchError):
    status_code = 500
    detail = "The research pipeline could not complete"
    code = "research_pipeline_failed"


class ResearchCancelledError(Exception):
    """Internal cooperative-cancellation signal used by the worker."""
