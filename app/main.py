from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from . import models, schemas
from .db import SessionLocal, init_db

app = FastAPI(title="Simple FastAPI App")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    # Create tables automatically for development/testing. Use Alembic for migrations in prod.
    init_db()


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}


@app.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ItemModel).filter(models.ItemModel.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", response_model=schemas.Item, status_code=201)
def create_item(item: schemas.Item, db: Session = Depends(get_db)):
    existing = db.query(models.ItemModel).filter(models.ItemModel.id == item.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item id already exists")
    db_item = models.ItemModel(id=item.id, name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
