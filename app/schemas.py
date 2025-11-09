from pydantic import BaseModel
from typing import Optional


class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class RekapRequest(BaseModel):
    instansi: int
    month: int
    year: int
    karyawan_id: Optional[int] = None
    jlh_hari_kerja: Optional[int] = None
    hadir: Optional[int] = None
    tidak_hadir: Optional[int] = None
    twm: Optional[int] = None
    t1: Optional[int] = None
    t2: Optional[int] = None
    t3: Optional[int] = None
    t4: Optional[int] = None
    twp: Optional[int] = None
    p1: Optional[int] = None
    p2: Optional[int] = None
    p3: Optional[int] = None
    p4: Optional[int] = None
    izin_sakit: Optional[int] = None
    tugas_bk: Optional[int] = None
    tanpa_keterangan: Optional[int] = None
