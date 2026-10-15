from fastapi import APIRouter, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.schemas import ApiResponse
from neuralshelf.db.session import check_database_connection

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=ApiResponse)
def liveness_check() -> ApiResponse:
    return ApiResponse(
        success=True,
        code=MessageCode.SERVICE_HEALTHY,
        message=Message.SERVICE_HEALTHY,
        data=[{"status": "alive"}],
    )


@router.get("/ready", response_model=ApiResponse)
def readiness_check():
    if not check_database_connection():
        response = ApiResponse(
            success=False,
            code=MessageCode.SERVICE_NOT_READY,
            message=Message.SERVICE_NOT_READY,
            data=[{"database": "unavailable"}],
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(response.model_dump()),
        )

    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.SERVICE_READY,
        data=[{"database": "connected"}],
    )
