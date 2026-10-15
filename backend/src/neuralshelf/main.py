import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from neuralshelf.api.v1.router import api_router
from neuralshelf.core.config import get_settings
from neuralshelf.core.constants import REQUEST_ID_HEADER
from neuralshelf.core.exceptions import ApplicationError
from neuralshelf.core.logging import configure_logging
from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.middleware import RequestContextMiddleware
from neuralshelf.core.schemas import ApiResponse
from neuralshelf.db import model_registry  # noqa: F401  (registers all models)

configure_logging()

logger = logging.getLogger(__name__)
settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    description="Document knowledge base and retrieval-augmented generation API.",
    version="0.1.0",
    debug=settings.debug,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Starlette runs the last-added middleware first, so request IDs are assigned
# before CORS and cover every response, including CORS preflight rejections.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # bearer tokens in headers; no cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
    expose_headers=[REQUEST_ID_HEADER, "Retry-After"],
)
app.add_middleware(RequestContextMiddleware)

_HTTP_ERROR_CODES = {
    404: (MessageCode.NOT_FOUND, Message.NOT_FOUND),
    405: (MessageCode.METHOD_NOT_ALLOWED, Message.METHOD_NOT_ALLOWED),
}


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    data: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    response = ApiResponse(
        success=False,
        code=code,
        message=message,
        data=data or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(response.model_dump()),
        headers=headers,
    )


@app.exception_handler(ApplicationError)
async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(
                str(part) for part in error["loc"] if part != "body"
            ),
            "message": (
                "Please enter a valid email address."
                if error["type"] == "value_error"
                and "email" in error["loc"]
                else error["msg"]
            ),
        }
        for error in exc.errors()
    ]

    return error_response(
        status_code=422,
        code=MessageCode.VALIDATION_ERROR,
        message=Message.VALIDATION_ERROR,
        data=errors,
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    code, message = _HTTP_ERROR_CODES.get(
        exc.status_code, (MessageCode.HTTP_ERROR, Message.HTTP_ERROR)
    )
    return error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled application error.")
    return error_response(
        status_code=500,
        code=MessageCode.INTERNAL_SERVER_ERROR,
        message=Message.INTERNAL_SERVER_ERROR,
    )


@app.get("/", response_model=ApiResponse, tags=["Root"])
def root() -> ApiResponse:
    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.SERVICE_HEALTHY,
        data=[
            {
                "name": settings.app_name,
                "docs": "/docs",
                "health": f"{settings.api_v1_prefix}/health/live",
            }
        ],
    )
