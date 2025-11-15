from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional


class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}

class PresensiKaryawanResponse(BaseModel):
    id: Optional[int] = None
    nip: Optional[str] = None
    name: Optional[str] = None
    group_id: Optional[int] = None
    imei: Optional[str] = None
    instansi_id: Optional[int] = None
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[date] = None
    jenis_kelamin: Optional[str] = None
    pendidikan_terakhir: Optional[str] = None
    alamat: Optional[str] = None
    golongan: Optional[str] = None
    kordinat: Optional[str] = None
    jabatan: Optional[str] = None
    eselon_id: Optional[int] = None
    pangkat_id: Optional[int] = None
    status_face: Optional[int] = None
    comment_face: Optional[str] = None
    verified_id: Optional[int] = None
    verified_date: Optional[datetime] = None
    presensi_face: Optional[int] = None

    model_config = {"from_attributes": True}

class PresensiKaryawanListResponse(BaseModel):
    count: int
    data: list[PresensiKaryawanResponse]

    # Pydantic v2: allow creating from attribute/ORM objects if needed
    model_config = {"from_attributes": True}

class RekapRequest(BaseModel):
    instansi: int
    month: int
    year: int
    # Either provide remote_url or use_ssh with SSH/db creds
    remote_url: Optional[str] = None
    use_ssh: Optional[bool] = False
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    db_host: Optional[str] = '127.0.0.1'
    db_port: Optional[int] = 3306
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = 'bkd_presensi'

class RekapTahunanRequest(BaseModel):
    instansi: int
    year: int
    # Either provide remote_url or use_ssh with SSH/db creds
    remote_url: Optional[str] = None
    use_ssh: Optional[bool] = False
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    db_host: Optional[str] = '127.0.0.1'
    db_port: Optional[int] = 3306
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = 'bkd_presensi'

class AnalasisKehadiranResponse(BaseModel):
    year: int
    month: int
    minimum_tk: int

class RekapKehadiranResponse(BaseModel):
    tahun: int
    bulan: int
    karyawan_id: int
    instansi_id: int
    jumlah_hari: int
    hadir: int
    tidak_hadir: int
    twm: int
    t1: int
    t2: int
    t3: int
    t4: int
    twp: int
    p1: int
    p2: int
    p3: int
    p4: int
    izin_sakit: int
    tugas_bk: int
    tanpa_keterangan: int

    model_config = {"from_attributes": True}

class RekapKehadiranListResponse(BaseModel):
    count: int
    data: list[RekapKehadiranResponse]

    # Pydantic v2: allow creating from attribute/ORM objects if needed
    model_config = {"from_attributes": True}