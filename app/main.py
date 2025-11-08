from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from . import models, schemas
from .db import SessionLocal, init_db
from .rekap import run_rekap
import os
try:
    # If python-dotenv is installed, automatically load a local .env file so the
    # API will read connection credentials from it without extra setup.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If dotenv isn't installed, rely on the environment being set externally.
    pass

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


@app.post("/rekap")
def rekap_endpoint(payload: schemas.RekapRequest):
    """Run rekap pipeline in-memory and return laporan as JSON list.

    This endpoint accepts a minimal payload (instansi, month, year). Connection
    credentials (remote DB URL or SSH + DB credentials) are read from environment
    variables if not provided in the request. This keeps the API body small and
    avoids sending secrets in requests.
    """
    # Determine remote_url or SSH mode from payload or environment
    remote_url = payload.remote_url or os.getenv('REMOTE_DATABASE_URL')

    use_ssh = bool(payload.use_ssh) or (os.getenv('SSH_HOST') is not None)

    ssh_host = payload.ssh_host or os.getenv('SSH_HOST')
    ssh_port = int(payload.ssh_port) if payload.ssh_port is not None else int(os.getenv('SSH_PORT', 22))
    ssh_user = payload.ssh_user or os.getenv('SSH_USER')
    ssh_password = payload.ssh_password or os.getenv('SSH_PASSWORD')

    db_host = payload.db_host or os.getenv('DB_HOST', '127.0.0.1')
    db_port = int(payload.db_port) if payload.db_port is not None else int(os.getenv('DB_PORT', 3306))
    db_user = payload.db_user or os.getenv('DB_USER')
    db_password = payload.db_password or os.getenv('DB_PASSWORD')
    db_name = payload.db_name or os.getenv('DB_NAME', 'bkd_presensi')

    # Validation: we need either remote_url (direct) or SSH credentials available
    if not remote_url and not use_ssh:
        raise HTTPException(status_code=400, detail="No remote DB configured: set REMOTE_DATABASE_URL or enable SSH in environment")

    # If using SSH mode, ensure required env vars / creds are present
    if use_ssh and not (ssh_host and ssh_user and db_user and db_password):
        raise HTTPException(status_code=400, detail="SSH mode enabled but SSH/DB credentials are missing in environment or request")

    try:
        df = run_rekap(
            payload.instansi,
            payload.month,
            payload.year,
            remote_url=remote_url,
            use_ssh=use_ssh,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # convert DataFrame to list of records
    result = df.to_dict(orient='records') if not df.empty else []
    return {"count": len(result), "data": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
