from sqlalchemy import Column, Integer, String, Text, PrimaryKeyConstraint, BigInteger, DateTime, Date
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

class PresensIKaryawanModel(Base):
    __tablename__ = "presensi_karyawan"

    id = Column(Integer, primary_key=True, index=True)
    nip = Column(String(191), nullable=False)
    name = Column(String(191), nullable=False)
    group_id = Column(BigInteger, nullable=False)
    imei = Column(String(191), nullable=True)
    instansi_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    tempat_lahir = Column(String(191), nullable=True)
    tanggal_lahir = Column(Date, nullable=True)
    jenis_kelamin = Column(String(191), nullable=True)
    pendidikan_terakhir = Column(String(191), nullable=True)
    alamat = Column(String(191), nullable=True)
    golongan = Column(String(191), nullable=True)
    kordinat = Column(String(255), nullable=True)
    jabatan = Column(String(255), nullable=True)
    eselon_id = Column(Integer, nullable=True)
    pangkat_id = Column(Integer, nullable=True)
    status_face = Column(Integer, nullable=True)
    comment_face = Column(String(255), nullable=True)
    verified_id = Column(Integer, nullable=True)
    verified_date = Column(DateTime, nullable=True)
    presensi_face = Column(Integer, nullable=True)

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