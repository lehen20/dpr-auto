class DocumentSearchException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class FileUploadException(DocumentSearchException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)


class GeminiAPIException(DocumentSearchException):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message, status_code)


class ValidationException(DocumentSearchException):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message, status_code)