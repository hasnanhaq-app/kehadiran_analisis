from __future__ import annotations

from typing import Optional, Tuple
from calendar import monthrange
from pathlib import Path

import pandas as pd
from sqlalchemy.exc import OperationalError
from sshtunnel import SSHTunnelForwarder
import pymysql

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
              db_host: str = '127.0.0.1', db_port: int = 3306, db_user: Optional[str] = None, db_password: Optional[str] = None, db_name: str = 'bkd_presensi') -> pd.DataFrame:
    """Fetch data (via direct engine or SSH), run generate_presensi_laporan and return the result DataFrame.

    This function keeps everything in-memory and does not write to local DB or Excel.
    """
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

    df_laporan = generate_presensi_laporan(df_pegawai, df_rencana_shift, df_presensi, df_absen, month, year, tanggal_awal, tanggal_akhir)

    # df_laporan = df_laporan[df_laporan['karyawan_id'] == 22777]
    
    # return df_laporan

    df_laporan_bulanan = generate_laporan_bulanan(df_laporan)

    return df_laporan_bulanan
# End of run_rekap