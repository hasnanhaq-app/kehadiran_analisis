import os
from pydoc import text
try:
    # If python-dotenv is installed, automatically load a local .env file so the
    # API will read connection credentials from it without extra setup.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If dotenv isn't installed, rely on the environment being set externally.
    pass

from calendar import month
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from . import models, schemas
from .db import SessionLocal, init_db
from .rekap import run_rekap, run_rekap_tahunan

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

@app.get("/data_karyawan", response_model=schemas.PresensiKaryawanListResponse, status_code=200)
def get_karyawan_data(karyawan_id: Optional[int] = None, instansi_id: Optional[int] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.PresensIKaryawanModel)
    if karyawan_id is not None:
        query = query.filter(models.PresensIKaryawanModel.id == karyawan_id)
    if instansi_id is not None:
        query = query.filter(models.PresensIKaryawanModel.instansi_id == instansi_id)
    karyawan_records = query.limit(limit).all()
    if not karyawan_records:
        return {"count": 0, "data": []}
    karyawan_list = []
    for record in karyawan_records:
        karyawan_list.append(schemas.PresensiKaryawanResponse.from_orm(record))
    return {
        "count": len(karyawan_list),
        "data": karyawan_list
    }


@app.get("/data_local_db_engine")
def get_local_data(instansi_id: int, tanggal_awal: str, tanggal_akhir: str):
    # get local data using _fetch_local_db in rekap.py

    try:
        from .rekap import _fetch_local_db
        df = _fetch_local_db(instansi_id, tanggal_awal, tanggal_akhir)
        result = df.to_dict(orient='records') if not df.empty else []
        res = _fetch_local_db(instansi_id, tanggal_awal, tanggal_akhir, return_meta=True)
        # support fuction that returns (df, meta) or df or list
        df = res[0] if isinstance(res, (tuple, list)) and len(res) > 2 else res
        if hasattr(df, 'empty'):
            result = df.to_dict(orient='records') if not df.empty else []
        else:
            result = df or []
        return {"count": len(result), "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rekap")
def rekap_endpoint(payload: schemas.RekapRequest):
    # """Run rekap pipeline in-memory and return laporan as JSON list.

    # This endpoint accepts a minimal payload (instansi, month, year). Connection
    # credentials (remote DB URL or SSH + DB credentials) are read from environment
    # variables if not provided in the request. This keeps the API body small and
    # avoids sending secrets in requests.
    # """
    # Determine remote_url or SSH mode from payload or environment

    # If month and year are in the future, raise error
    if payload.year > datetime.now().year or (payload.year == datetime.now().year and payload.month > datetime.now().month):
        raise HTTPException(status_code=400, detail="Tidak bisa mencetak laporan untuk bulan yang belum berjalan.")
    
    remote_url = payload.remote_url or os.getenv('REMOTE_DATABASE_URL')

    use_ssh = bool(payload.use_ssh) or (os.getenv('SSH_HOST') is not None)

    ssh_host = payload.ssh_host or os.getenv('SSH_HOST')
    ssh_port = int(os.getenv('SSH_PORT', 22))
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

@app.post("/rekap_tahunan")
def rekap_tahunan_endpoint(payload: schemas.RekapTahunanRequest):

    # If month and year are in the future, raise error
    if payload.year > datetime.now().year:
        raise HTTPException(status_code=400, detail="Tidak bisa mencetak laporan untuk tahun yang belum berjalan.")

    # Similar to /rekap but for annual recap
    remote_url = payload.remote_url or os.getenv('REMOTE_DATABASE_URL')

    use_ssh = bool(payload.use_ssh) or (os.getenv('SSH_HOST') is not None)

    ssh_host = payload.ssh_host or os.getenv('SSH_HOST')
    ssh_port = int(os.getenv('SSH_PORT', 22))
    ssh_user = payload.ssh_user or os.getenv('SSH_USER')
    ssh_password = payload.ssh_password or os.getenv('SSH_PASSWORD')

    db_host = payload.db_host or os.getenv('DB_HOST', '127.0.0.1')
    db_port = int(payload.db_port) if payload.db_port is not None else int(os.getenv('DB_PORT', 3306))
    db_user = payload.db_user or os.getenv('DB_USER')
    db_password = payload.db_password or os.getenv('DB_PASSWORD')
    db_name = payload.db_name or os.getenv('DB_NAME', 'bkd_presensi')

    if not remote_url and not use_ssh:
        raise HTTPException(status_code=400, detail="No remote DB configured: set REMOTE_DATABASE_URL or enable SSH in environment")
    if use_ssh and not (ssh_host and ssh_user and db_user and db_password):
        raise HTTPException(status_code=400, detail="SSH mode enabled but SSH/DB credentials are missing in environment or request")
    try:
        df = run_rekap_tahunan(
            payload.instansi,
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
    
    result = df.to_dict(orient='records') if not df.empty else []
    return {"count": len(result), "data": result}

@app.post("/analisis_kehadiran")
def api_analisis_kehadiran(payload: schemas.AnalasisKehadiranResponse):
    """
    Analyze sum of `tanpa_keterangan` in `rekap_bulanan` for given year and month.
    Returns a list of rows with instansi_id and total_tanpa_keterangan.
    """
    try:
        # import here to avoid import-time side effects / circular imports
        from .analisis import analisis_kehadiran

        results = analisis_kehadiran(year=payload.year, month=payload.month, minimum_tk=payload.minimum_tk)
        return {"count": len(results), "data": results}
        # return payload
    except Exception as e:
        # keep message short and return 500
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/rekap_kehadiran", response_model=schemas.RekapKehadiranListResponse, status_code=200)
def api_hasil_analisis(tahun: int, bulan: Optional[int] = None, karyawan_id: Optional[int] = None, instansi_id: Optional[int] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(models.RekapKehadiranModel).filter(
            models.RekapKehadiranModel.tahun == tahun,
        )
        if bulan is not None:
            if bulan < 1 or bulan > 12:
                raise HTTPException(status_code=400, detail="Bulan harus antara 1 dan 12.")
            
            query = query.filter(models.RekapKehadiranModel.bulan == bulan)

        if karyawan_id is not None:
            query = query.filter(models.RekapKehadiranModel.karyawan_id == karyawan_id)
        
        if instansi_id is not None:
            query = query.filter(models.RekapKehadiranModel.instansi_id == instansi_id)

        # get all matching records ordered by instansi_id karyawan_id, tahun, bulan
        rekap_record = query.order_by(
            models.RekapKehadiranModel.instansi_id,
            models.RekapKehadiranModel.karyawan_id,
            models.RekapKehadiranModel.tahun,
            models.RekapKehadiranModel.bulan
        ).all()

        if not rekap_record:
            return {"count": 0, "data": []}
    
        rekap_list = [schemas.RekapKehadiranResponse.from_orm(r) for r in rekap_record]

        return {
            "count": len(rekap_list),
            "data": rekap_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
