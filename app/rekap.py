from __future__ import annotations

from typing import Optional, Tuple
from calendar import monthrange
from pathlib import Path

import pandas as pd
from sqlalchemy.exc import OperationalError
from sshtunnel import SSHTunnelForwarder
import pymysql

import os
from dotenv import load_dotenv

import datetime

from .analytics import get_engine
from .presensi import generate_presensi_laporan, generate_laporan_bulanan


def _fetch_via_ssh(ssh_host: str, ssh_port: int, ssh_user: str, ssh_password: Optional[str],
                   db_host: str, db_port: int, db_user: str, db_password: str, db_name: str,
                   instansi_id: int, tanggal_awal: str, tanggal_akhir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        remote_bind_address=(db_host, db_port),
        local_bind_address=('127.0.0.1', 10022),
    ) as tunnel:
        conn = pymysql.connect(host='127.0.0.1', port=10022, user=db_user, password=db_password, db=db_name)

        df_pegawai = pd.read_sql("SELECT * FROM presensi_karyawan WHERE instansi_id = %s", conn, params=[instansi_id])

        df_presensi = pd.read_sql(
            "SELECT * FROM presensi_kehadiran WHERE instansi_id = %s AND date(tanggal_masuk) BETWEEN %s AND %s",
            conn, params=[instansi_id, tanggal_awal, tanggal_akhir]
        )

        df_rencana = pd.read_sql(
            "SELECT * FROM presensi_rencana_shift WHERE instansi_id = %s AND date(tanggal_masuk) BETWEEN %s AND %s",
            conn, params=[instansi_id, tanggal_awal, tanggal_akhir]
        )

        df_shift = pd.read_sql("SELECT * FROM presensi_shift", conn)

        df_absen = pd.read_sql(
            "SELECT presensi_absen.* FROM presensi_absen LEFT JOIN presensi_karyawan ON presensi_absen.karyawan_id = presensi_karyawan.id WHERE presensi_karyawan.instansi_id = %s",
            conn, params=[instansi_id]
        )

        conn.close()

    return df_pegawai, df_rencana, df_presensi, df_shift, df_absen
# End of _fetch_via_ssh

# Fetch data to Local DB using SQLAlchemy engine and using pydantic models
def _fetch_local_db(instansi_id: int, tanggal_awal: str, tanggal_akhir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    engine = get_engine(None)  # get local engine from env DATABASE_URL
    with engine.connect() as conn:
        df_pegawai = pd.read_sql_query(f"SELECT * FROM presensi_karyawan WHERE instansi_id = {instansi_id}", conn)

        df_presensi = pd.read_sql_query(
            f"SELECT * FROM presensi_kehadiran WHERE instansi_id = {instansi_id} AND date(tanggal_masuk) BETWEEN '{tanggal_awal}' AND '{tanggal_akhir}'",
            conn,
        )

        df_rencana = pd.read_sql_query(
            f"SELECT * FROM presensi_rencana_shift WHERE instansi_id = {instansi_id} AND date(tanggal_masuk) BETWEEN '{tanggal_awal}' AND '{tanggal_akhir}'",
            conn,
        )

        df_shift = pd.read_sql_query("SELECT * FROM presensi_shift", conn)

        df_absen = pd.read_sql_query(
            f"SELECT presensi_absen.* FROM presensi_absen LEFT JOIN presensi_karyawan ON presensi_absen.karyawan_id = presensi_karyawan.id WHERE presensi_karyawan.instansi_id = {instansi_id}",
            conn,
        )

    return df_pegawai, df_rencana, df_presensi, df_shift, df_absen


def _fetch_via_engine(remote_url: str, instansi_id: int, tanggal_awal: str, tanggal_akhir: str):
    engine = get_engine(remote_url)
    with engine.connect() as conn:
        # Some DBs (like SQLite used for testing) may not have schema prefixes; queries are written conservatively
        try:
            df_pegawai = pd.read_sql_query(f"SELECT * FROM presensi_karyawan WHERE instansi_id = {instansi_id}", conn)

            df_presensi = pd.read_sql_query(
                f"SELECT * FROM presensi_kehadiran WHERE instansi_id = {instansi_id} AND date(tanggal_masuk) BETWEEN '{tanggal_awal}' AND '{tanggal_akhir}'",
                conn,
            )

            df_rencana = pd.read_sql_query(
                f"SELECT * FROM presensi_rencana_shift WHERE instansi_id = {instansi_id} AND date(tanggal_masuk) BETWEEN '{tanggal_awal}' AND '{tanggal_akhir}'",
                conn,
            )

            df_shift = pd.read_sql_query("SELECT * FROM presensi_shift", conn)

            df_absen = pd.read_sql_query(
                f"SELECT presensi_absen.* FROM presensi_absen LEFT JOIN presensi_karyawan ON presensi_absen.karyawan_id = presensi_karyawan.id WHERE presensi_karyawan.instansi_id = {instansi_id}",
                conn,
            )
        except OperationalError:
            # Fallback for simple/local DBs where instansi_id or schema prefixes may be missing.
            df_pegawai = pd.read_sql_query("SELECT * FROM presensi_karyawan", conn)
            df_presensi = pd.read_sql_query(
                f"SELECT * FROM presensi_kehadiran WHERE date(tanggal_masuk) BETWEEN '{tanggal_awal}' AND '{tanggal_akhir}'",
                conn,
            )
            df_rencana = pd.read_sql_query(
                f"SELECT * FROM presensi_rencana_shift WHERE date(tanggal_masuk) BETWEEN '{tanggal_awal}' AND '{tanggal_akhir}'",
                conn,
            )
            df_shift = pd.read_sql_query("SELECT * FROM presensi_shift", conn)
            df_absen = pd.read_sql_query("SELECT * FROM presensi_absen", conn)

    return df_pegawai, df_rencana, df_presensi, df_shift, df_absen
# End of _fetch_via_engine


def run_rekap(instansi: int, month: int, year: int, *, remote_url: Optional[str] = None, use_ssh: bool = False,
              ssh_host: Optional[str] = None, ssh_port: int = 22, ssh_user: Optional[str] = None, ssh_password: Optional[str] = None,
              db_host: str = '127.0.0.1', db_port: int = 3306, db_user: Optional[str] = None, db_password: Optional[str] = None, db_name: str = 'bkd_presensi',
              local_url: Optional[str] = None, save_raw: bool = False) -> pd.DataFrame:
    """Fetch data (via direct engine or SSH), run generate_presensi_laporan and return the result DataFrame.

    This function keeps everything in-memory and does not write to local DB or Excel.
    """
    now = datetime.datetime.now()

    # Jika yang dicetak lebih dari bulan sekarang di tahun ini, batalkan
    if year > now.year or (year == now.year and month > now.month):
        raise ValueError("Tidak bisa mencetak laporan untuk bulan yang belum berjalan.")

    # Jika yang dicetak tahun ini, maka bulan yang diambil hanya sampai bulan sekarang. Dan jika yang dicetak bulan ini, maka hari yang diambil hanya sampai hari sekarang.

    if year == now.year and month == now.month:
        last_day = now.day
    
    
    # compose tanggal_awal / akhir
    _, last_day = monthrange(year, month)
    tanggal_awal = f"{year:04d}-{month:02d}-01"
    tanggal_akhir = f"{year:04d}-{month:02d}-{last_day:02d}"

    if use_ssh:
        if not all([ssh_host, ssh_user, db_user, db_password]):
            raise ValueError('SSH mode requires ssh_host, ssh_user, db_user and db_password')
        df_pegawai, df_rencana, df_presensi, df_shift, df_absen = _fetch_via_ssh(
            ssh_host, ssh_port, ssh_user, ssh_password,
            db_host, db_port, db_user, db_password, db_name,
            instansi, tanggal_awal, tanggal_akhir
        )
    else:
        if not remote_url:
            raise ValueError('remote_url must be provided when not using SSH')
        df_pegawai, df_rencana, df_presensi, df_shift, df_absen = _fetch_via_engine(remote_url, instansi, tanggal_awal, tanggal_akhir)

    # Optionally save the raw fetched tables to a local DB
    if save_raw:
        # get local engine (prefer explicit local_url, then env DATABASE_URL)
        try:
            from .analytics import get_engine

            local_engine = get_engine(local_url)
        except Exception:
            local_engine = None

        if local_engine is None:
            raise ValueError("save_raw=True but no local database available (set local_url or DATABASE_URL)")

        # write DataFrames to local DB replacing existing content for an idempotent snapshot
        try:
            with local_engine.begin() as conn:
                # choose table names matching source
                df_pegawai.to_sql('presensi_karyawan', conn, if_exists='replace', index=False)
                df_rencana.to_sql('presensi_rencana_shift', conn, if_exists='replace', index=False)
                df_presensi.to_sql('presensi_kehadiran', conn, if_exists='replace', index=False)
                df_shift.to_sql('presensi_shift', conn, if_exists='replace', index=False)
                df_absen.to_sql('presensi_absen', conn, if_exists='replace', index=False)
        except Exception as e:
            # fail early and surface the error
            raise

    # merge rencana + shift similar to script
    if 'shift_id' in df_rencana.columns:
        df_rencana_shift = df_rencana.merge(df_shift, left_on='shift_id', right_on='id', how='left')
    else:
        df_rencana_shift = df_rencana

    # normalize/parse columns
    if 'tanggal_masuk' in df_rencana_shift.columns:
        df_rencana_shift['tanggal_masuk'] = pd.to_datetime(df_rencana_shift['tanggal_masuk'], errors='coerce')

    for time_col in ['masuk_pre_time', 'masuk_post_time', 'masuk_max_time', 'pulang_pre_time', 'pulang_post_time', 'jam_masuk', 'jam_pulang']:
        if time_col in df_rencana_shift.columns:
            try:
                df_rencana_shift[time_col] = df_rencana_shift['tanggal_masuk'] + pd.to_timedelta(df_rencana_shift[time_col])
            except Exception:
                df_rencana_shift[time_col] = pd.to_datetime(df_rencana_shift[time_col], errors='coerce')

    if 'tanggal_mulai' in df_absen.columns:
        df_absen['tanggal_mulai'] = pd.to_datetime(df_absen['tanggal_mulai'], errors='coerce')
    if 'tanggal_selesai' in df_absen.columns:
        df_absen['tanggal_selesai'] = pd.to_datetime(df_absen['tanggal_selesai'], errors='coerce')

    if 'tanggal_masuk' in df_presensi.columns:
        df_presensi['tanggal_masuk'] = pd.to_datetime(df_presensi['tanggal_masuk'], errors='coerce')
    if 'tanggal_kirim' in df_presensi.columns:
        df_presensi['tanggal_kirim'] = pd.to_datetime(df_presensi['tanggal_kirim'], errors='coerce')

    # simpan_data_karyawan(df_pegawai)

    df_laporan = generate_presensi_laporan(df_pegawai, df_rencana_shift, df_presensi, df_absen, month, year, tanggal_awal, tanggal_akhir)

    # df_laporan = df_laporan[df_laporan['karyawan_id'] == 22777]
    
    # return df_laporan

    df_laporan_bulanan = generate_laporan_bulanan(df_laporan)

    df_laporan_bulanan['instansi_id'] = instansi
    df_laporan_bulanan['tahun'] = year
    df_laporan_bulanan['bulan'] = month

    # menyimpan hasil rekap ke local db
    # df_laporan_bulanan ditambahkan kolom instansi_id, tahun dan bulan

    simpan_rekap_bulanan(df_laporan_bulanan)

    return df_laporan_bulanan
# End of run_rekap

def run_rekap_tahunan(instansi: int, year: int, *, remote_url: Optional[str] = None, use_ssh: bool = False,
              ssh_host: Optional[str] = None, ssh_port: int = 22, ssh_user: Optional[str] = None, ssh_password: Optional[str] = None,
              db_host: str = '127.0.0.1', db_port: int = 3306, db_user: Optional[str] = None, db_password: Optional[str] = None, db_name: str = 'bkd_presensi') -> pd.DataFrame:
    """Run rekap for all months in the given year and return the concatenated DataFrame.
    """
    df_list = []

    # jika yang dicetak tahun ini, maka bulan yang diambil hanya sampai bulan sekarang
    
    now = datetime.datetime.now()
    if year == now.year:
        end_month = now.month
    else:
        end_month = 12
    
    for month in range(1, end_month + 1):
        df_monthly = run_rekap(
            instansi, month, year,
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
        df_list.append(df_monthly)
    df_yearly = pd.concat(df_list, ignore_index=True)
    return df_yearly
# End of run_rekap_tahunan

def simpan_data_karyawan(df_pegawai: pd.DataFrame) -> None:

    local_db_connection = local_db_connection()

    insert_query = """
    INSERT INTO presensi_karyawan (
        id, nip, name, group_id, imei, instansi_id, created_at, updated_at, deleted_at, tempat_lahir, tanggal_lahir, pendidikan_terakhir, alamat, golongan, kordinat, jabatan, eselon_id, pangkat_id, status_face, comment_face, verified_date, presensi_face
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        nip=VALUES(nip),
        name=VALUES(name),
        group_id=VALUES(group_id),
        imei=VALUES(imei),
        instansi_id=VALUES(instansi_id),
        created_at=VALUES(created_at),
        updated_at=VALUES(updated_at),
        deleted_at=VALUES(deleted_at),
        tempat_lahir=VALUES(tempat_lahir),
        tanggal_lahir=VALUES(tanggal_lahir),
        pendidikan_terakhir=VALUES(pendidikan_terakhir),
        alamat=VALUES(alamat),
        golongan=VALUES(golongan),
        kordinat=VALUES(kordinat),
        jabatan=VALUES(jabatan),
        eselon_id=VALUES(eselon_id),
        pangkat_id=VALUES(pangkat_id),
        status_face=VALUES(status_face),
        comment_face=VALUES(comment_face),
        verified_date=VALUES(verified_date),
        presensi_face=VALUES(presensi_face) 
    """

    with local_db_connection.cursor() as cursor:
        for _, row in df_pegawai.iterrows():
            cursor.execute(insert_query, (
                row['id'],
                row['nip'],
                row['name'],
                row['group_id'],
                row['imei'],
                row['instansi_id'],
                row['created_at'],
                row['updated_at'],
                row['deleted_at'],
                row['tempat_lahir'],
                row['tanggal_lahir'],
                row['pendidikan_terakhir'],
                row['alamat'],
                row['golongan'],
                row['kordinat'],
                row['jabatan'],
                row['eselon_id'],
                row['pangkat_id'],
                row['status_face'],
                row['comment_face'],
                row['verified_date'],
                row['presensi_face']
            ))
        local_db_connection.commit()
    local_db_connection.close()


def simpan_rekap_bulanan(df_laporan_bulanan: pd.DataFrame) -> None:
    """Simpan df_laporan_bulanan ke local DB dengan menambahkan kolom instansi_id, tahun, bulan."""

    local_db_connection = pymysql.connect(
        host=os.getenv('DB_HOST_LOCAL', 'localhost'),
        port=int(os.getenv('DB_PORT_LOCAL', 3306)),
        user=os.getenv('DB_USER_LOCAL', 'root'),
        password=os.getenv('DB_PASSWORD_LOCAL', ''),
        db=os.getenv('DB_NAME_LOCAL', 'bkd_presensi')
    )
    
    insert_query = """
    INSERT INTO rekap_bulanan (
        karyawan_id, instansi_id, tahun, bulan, jumlah_hari, hadir, tidak_hadir, twm, t1, t2, t3, t4, twp, p1, p2, p3, p4, izin_sakit, tugas_bk, tanpa_keterangan
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        jumlah_hari=VALUES(jumlah_hari),
        hadir=VALUES(hadir),
        tidak_hadir=VALUES(tidak_hadir),
        twm=VALUES(twm),
        t1=VALUES(t1),
        t2=VALUES(t2),
        t3=VALUES(t3),
        t4=VALUES(t4),
        twp=VALUES(twp),
        p1=VALUES(p1),
        p2=VALUES(p2),
        p3=VALUES(p3),
        p4=VALUES(p4),
        izin_sakit=VALUES(izin_sakit),
        tugas_bk=VALUES(tugas_bk),
        tanpa_keterangan=VALUES(tanpa_keterangan)
    """

    with local_db_connection.cursor() as cursor:
        for _, row in df_laporan_bulanan.iterrows():
            cursor.execute(insert_query, (
                row['karyawan_id'],
                row['instansi_id'],
                row['tahun'],
                row['bulan'],
                row['jumlah_hari'],
                row['hadir'],
                row['tidak_hadir'],
                row['twm'],
                row['t1'],
                row['t2'],
                row['t3'],
                row['t4'],
                row['twp'],
                row['p1'],
                row['p2'],
                row['p3'],
                row['p4'],
                row['izin_sakit'],
                row['tugas_bk'],
                row['tanpa_keterangan']
            ))
        local_db_connection.commit()
    local_db_connection.close()