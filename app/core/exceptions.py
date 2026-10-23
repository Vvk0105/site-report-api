from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import logger


def _error_body(message, errors=None) -> dict:
    # `detail` is read by the admin panel, `message` by the mobile app.
    body = {"success": False, "message": message, "detail": message}
    if errors is not None:
        body["errors"] = errors
    return body


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        messages = [
            f"{'.'.join(str(p) for p in err.get('loc', [])[1:])}: {err.get('msg')}"
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body("; ".join(messages) or "Invalid request", errors=exc.errors()),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("Internal Server Error"),
        )
