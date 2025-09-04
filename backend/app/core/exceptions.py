from typing import Any, Dict, Optional
from fastapi import HTTPException

class OpenHubException(Exception):
    """基础异常类"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class ValidationError(OpenHubException):
    """验证错误"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")

class NotFoundError(OpenHubException):
    """资源未找到错误"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND")

class PermissionError(OpenHubException):
    """权限错误"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "PERMISSION_DENIED")

class IPMIError(OpenHubException):
    """IPMI操作错误"""
    def __init__(self, message: str):
        super().__init__(message, "IPMI_ERROR")

# 全局异常处理
async def openhub_exception_handler(request, exc: OpenHubException):
    return HTTPException(
        status_code=400,
        detail={
            "code": exc.code,
            "message": exc.message
        }
    )