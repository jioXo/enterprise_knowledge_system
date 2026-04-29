from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging
from src.utils.auth import auth_manager
from src.utils.logger import logger_manager

logger = logger_manager.get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        # 白名单路径
        public_paths = [
            "/",
            "/docs",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/login",
            "/api/v1/register"
        ]

        # 检查是否为公开路径
        if request.url.path in public_paths:
            return await call_next(request)

        # 检查Authorization头
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing"
            )

        # 验证token格式
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme"
                )
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )

        # 验证token
        payload = auth_manager.verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        # 将用户信息添加到请求中
        request.state.user_id = payload.get("user_id")
        request.state.user_role = payload.get("role")

        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # 记录请求
        logger.info(
            f"Request started - {request.method} {request.url.path}"
        )

        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 记录响应
            logger_manager.log_api_metrics(
                logger,
                request.url.path,
                request.method,
                process_time,
                response.status_code
            )

            # 添加处理时间头
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 记录错误
            logger_manager.log_error(logger, e)
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}

    async def dispatch(self, request: Request, call_next: Callable):
        # 简单的IP限流实现
        client_ip = request.client.host
        current_time = int(time.time() // 60)  # 每分钟重置

        # 初始化或重置计数器
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {}

        if current_time not in self.request_counts[client_ip]:
            self.request_counts[client_ip][current_time] = 0

        # 检查是否超限
        if self.request_counts[client_ip][current_time] >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )

        # 增加计数
        self.request_counts[client_ip][current_time] += 1

        response = await call_next(request)
        return response


class CORSHeadersMiddleware(BaseHTTPMiddleware):
    """CORS中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # 添加CORS头
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"

        return response


class ContentLengthMiddleware(BaseHTTPMiddleware):
    """内容长度中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # 记录响应内容长度
        content_length = len(response.body) if hasattr(response, 'body') else 0
        response.headers["Content-Length"] = str(content_length)

        return response