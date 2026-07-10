from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request

from fastapi.responses import JSONResponse
from app.core.logger import logger

def register_exception_handlers(
    app: FastAPI,
):

    @app.exception_handler(
        HTTPException
    )
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
            },
        )

    @app.exception_handler(
        Exception
    )
    async def exception_handler(
        request: Request,
        exc: Exception,
    ):

        logger.exception(exc)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
            },
        )