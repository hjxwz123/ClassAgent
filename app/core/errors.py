from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, message: str, code: int = 1):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def bad_request(message: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, message)


def unauthorized(message: str = "未认证或令牌无效") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, message)


def forbidden(message: str = "无权限访问该资源") -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, message)


def not_found(message: str = "资源不存在") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, message)
