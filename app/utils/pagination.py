import math


def paginate(
    *,
    total: int,
    page: int,
    page_size: int,
    results,
):

    total_pages = (
        math.ceil(total / page_size)
        if total
        else 1
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
        "results": results,
    }