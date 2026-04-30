from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException, status

ExceptionStatusMap = Sequence[tuple[type[BaseException], int]]


###############################################################################
def http_exception_for_exception(
    exc: BaseException,
    status_map: ExceptionStatusMap,
    *,
    default_detail: str,
    default_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> HTTPException:
    for exception_type, status_code in status_map:
        if isinstance(exc, exception_type):
            detail = str(exc)
            if exception_type is KeyError:
                detail = detail.strip("'")
            return HTTPException(
                status_code=status_code,
                detail=detail,
            )
    return HTTPException(
        status_code=default_status_code,
        detail=default_detail,
    )
