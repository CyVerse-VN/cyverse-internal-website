class AuthenticationError(Exception):
    """Base error for authentication and account administration failures."""

    status_code = 400
    detail = "Authentication request failed"


class InvalidCredentialsError(AuthenticationError):
    status_code = 401
    detail = "Invalid username or password"


class InvalidCurrentPasswordError(AuthenticationError):
    status_code = 400
    detail = "Current password is incorrect"


class PasswordReuseError(AuthenticationError):
    status_code = 400
    detail = "New password must be different from the current password"


class AuthenticationRequiredError(AuthenticationError):
    status_code = 401
    detail = "Authentication required"


class PermissionDeniedError(AuthenticationError):
    status_code = 403
    detail = "You do not have permission to perform this action"


class UserNotFoundError(AuthenticationError):
    status_code = 404
    detail = "User not found"


class UsernameConflictError(AuthenticationError):
    status_code = 409
    detail = "Username already exists"


class AccountInvariantError(AuthenticationError):
    status_code = 409
    detail = "This change would leave the application without an active administrator"


class SelfAdministrationError(AuthenticationError):
    status_code = 409
    detail = "Administrators cannot deactivate or demote their own account"
