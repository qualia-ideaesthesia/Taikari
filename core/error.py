class ArcError(Exception):
    def __init__(self, message=None, error_code=108, api_error_code=-999, extra_data=None, status=200) -> None:
        self.message: str = message
        self.error_code: int = error_code
        self.api_error_code: int = api_error_code
        self.extra_data = extra_data
        self.status: int = status

    def __str__(self) -> str:
        return repr(self.message)


class InputError(ArcError):
    '''Input type error'''

    def __init__(self, message=None, error_code=108, api_error_code=-100, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class DataExist(ArcError):
    '''Data exists'''

    def __init__(self, message=None, error_code=108, api_error_code=-4, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class NoData(ArcError):
    '''Data does not exist'''

    def __init__(self, message=None, error_code=108, api_error_code=-2, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class PostError(ArcError):
    '''Missing input'''

    def __init__(self, message=None, error_code=108, api_error_code=-100, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class UserBan(ArcError):
    '''User banned'''

    def __init__(self, message=None, error_code=121, api_error_code=-202, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class ItemNotEnough(ArcError):
    '''Not enough items'''

    def __init__(self, message=None, error_code=-6, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class ItemUnavailable(ArcError):
    '''Item unavailable'''

    def __init__(self, message=None, error_code=-6, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class RedeemUnavailable(ArcError):
    '''Redeem code unavailable'''

    def __init__(self, message=None, error_code=505, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class MapLocked(ArcError):
    '''Map locked'''

    def __init__(self, message=None, error_code=108, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class StaminaNotEnough(ArcError):
    '''Not enough stamina'''

    def __init__(self, message=None, error_code=107, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class TicketNotEnough(ArcError):
    '''Not enough memory source points'''

    def __init__(self, message=None, error_code=-6, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class FriendError(ArcError):
    '''Friend system error'''

    def __init__(self, message=None, error_code=108, api_error_code=-999, extra_data=None, status=200) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class NoAccess(ArcError):
    '''No permission'''

    def __init__(self, message=None, error_code=108, api_error_code=-999, extra_data=None, status=403) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class LowVersion(ArcError):
    '''Version too low'''

    def __init__(self, message=None, error_code=5, api_error_code=-999, extra_data=None, status=403) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class Timeout(ArcError):
    '''Timeout'''
    pass


class RateLimit(ArcError):
    '''Rate limit reached'''

    def __init__(self, message=None, error_code=108, api_error_code=-999, extra_data=None, status=429) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)


class ConfigError(ArcError):
    '''Config error'''

    def __init__(self, message=None, error_code=108, api_error_code=-999, extra_data=None, status=500) -> None:
        super().__init__(message, error_code, api_error_code, extra_data, status)
