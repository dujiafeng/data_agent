import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_context_var

app = FastAPI(lifespan=lifespan)

app.include_router(query_router)

@app.middleware("http")
async def add_process_time_handle(request: Request, call_next):
    # 请求被处理之前
    request_id = uuid.uuid4()
    request_id_context_var.set(request_id)

    response = await call_next(request)
    return response

if __name__ == '__main__':
    pass
