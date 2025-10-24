from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

app = FastAPI(title="Simple FastAPI App")

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

# In-memory store for demo purposes
_items: Dict[int, Item] = {}

@app.get("/")
async def read_root():
    return {"message": "Hello from FastAPI"}

@app.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int):
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/items", response_model=Item, status_code=201)
async def create_item(item: Item):
    if item.id in _items:
        raise HTTPException(status_code=400, detail="Item id already exists")
    _items[item.id] = item
    return item

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
