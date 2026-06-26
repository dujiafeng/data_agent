import asyncio

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from app.api.schemas.query_schema import QuerySchema

query_router = APIRouter()


async def fake_streamer():
    for i in range(10):
        await asyncio.sleep(1)
        yield f"data: step: {i} \n\n"


@query_router.post("/api/query")
async def query_handler(query: QuerySchema):
    return StreamingResponse(fake_streamer(),media_type="text/event-stream")