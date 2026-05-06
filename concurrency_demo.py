import asyncio

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()


class Item(BaseModel):
    text: str


@app.post("/index")
async def index_item(item: Item):
    print(f"Indexing item: {item.text}")
    await asyncio.sleep(2)
    return {"message": f"Item {item.text} indexed"}


@app.post("/query")
async def query_item(item: Item):
    print(f"Querying item: {item.text}")
    await asyncio.sleep(1)
    return {"message": f"Item {item.text} found"}
