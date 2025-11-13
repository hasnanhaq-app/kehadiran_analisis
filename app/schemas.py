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