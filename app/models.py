from sqlalchemy import Column, Integer, String, Text, PrimaryKeyConstraint
from .db import Base


class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)

class RekapKehadiranModel(Base):
    __tablename__ = "rekap_bulanan"
    __table_args__ = (PrimaryKeyConstraint('karyawan_id','tahun','bulan'),)

    karyawan_id = Column(Integer, nullable=False)
    tahun = Column(Integer, nullable=False)
    bulan = Column(Integer, nullable=False)
    instansi_id = Column(Integer, nullable=False)
    jumlah_hari = Column(Integer, nullable=False)
    hadir = Column(Integer, nullable=False)
    tidak_hadir = Column(Integer, nullable=False)
    twm = Column(Integer, nullable=False)
    t1 = Column(Integer, nullable=False)
    t2 = Column(Integer, nullable=False)
    t3 = Column(Integer, nullable=False)
    t4 = Column(Integer, nullable=False)
    twp = Column(Integer, nullable=False)
    p1 = Column(Integer, nullable=False)
    p2 = Column(Integer, nullable=False)
    p3 = Column(Integer, nullable=False)
    p4 = Column(Integer, nullable=False)
    izin_sakit = Column(Integer, nullable=False)
    tugas_bk = Column(Integer, nullable=False)
    tanpa_keterangan = Column(Integer, nullable=False)