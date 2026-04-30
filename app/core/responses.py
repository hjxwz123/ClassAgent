from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(data=None, message: str = "ok", code: int = 0, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "code": code,
                "message": message,
                "data": data,
                "request_id": request_id or str(uuid4()),
            }
        ),
    )


def paginated_response(items, total: int, page: int, page_size: int, request_id: str | None = None) -> JSONResponse:
    return success_response(
        data={
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        },
        request_id=request_id,
    )
