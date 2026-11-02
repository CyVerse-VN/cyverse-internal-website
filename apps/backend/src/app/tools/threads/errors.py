class ThreadsError(Exception):
    def __init__(self, code: str, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class ThreadsCancelled(ThreadsError):
    def __init__(self) -> None:
        super().__init__("RUN_CANCELLED", "The Threads run was cancelled.", 409)
