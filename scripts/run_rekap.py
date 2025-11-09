"""Run the rekap (attendance) pipeline: fetch remote tables, transform, store locally.

Supports two fetching modes:
- SSH tunneling (if --use-ssh flag is set) using the same pattern as the notebook
  (SSHTunnelForwarder + pymysql).
- Direct DB access via SQLAlchemy engine (pass --remote-url). The script uses
  pandas.read_sql to load the tables and then runs `generate_presensi_laporan`.

Example usage:
    export DATABASE_URL='sqlite:///./local.db'
    export REMOTE_DATABASE_URL='mysql+pymysql://user:pass@host:3306/bkd_presensi'
    python scripts/run_rekap.py --instansi 3062 --month 10 --year 2025

Or for SSH mode (supply SSH_HOST, SSH_PORT, SSH_USER, SSH_PASSWORD env vars or pass args):
    python scripts/run_rekap.py --use-ssh --ssh-host my.host --ssh-port 22 --ssh-user root --ssh-password secret --instansi 3062 --month 10 --year 2025
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from sshtunnel import SSHTunnelForwarder
import pymysql

from app.presensi import generate_presensi_laporan
from app.analytics import get_engine


def fetch_via_ssh(ssh_host: str, ssh_port: int, ssh_user: str, ssh_password: Optional[str], db_host: str, db_port: int, db_user: str, db_password: str, db_name: str, instansi_id: int, tanggal_awal: str, tanggal_akhir: str):
    with SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        remote_bind_address=(db_host, db_port),
        local_bind_address=('127.0.0.1', 10022),
    ) as tunnel:
        conn = pymysql.connect(host='127.0.0.1', port=10022, user=db_user, password=db_password, db=db_name)

        df_pegawai = pd.read_sql("""
            SELECT * FROM bkd_presensi.presensi_karyawan
            WHERE instansi_id = %s
        """, conn, params=[instansi_id])

        df_presensi = pd.read_sql(
            """
            SELECT * FROM bkd_presensi.presensi_kehadiran
            WHERE instansi_id = %s AND date(tanggal_masuk) BETWEEN %s AND %s
            """,
            conn,
            params=[instansi_id, tanggal_awal, tanggal_akhir],
        )

        df_rencana = pd.read_sql(
            """
            SELECT * FROM bkd_presensi.presensi_rencana_shift
            WHERE instansi_id = %s AND date(tanggal_masuk) BETWEEN %s AND %s
            """,
            conn,
            params=[instansi_id, tanggal_awal, tanggal_akhir],
        )

        df_shift = pd.read_sql("SELECT * FROM presensi_shift", conn)

        # presensi_absen may not have instansi_id column; filter using joined presensi_karyawan
        df_absen = pd.read_sql(
            """
            SELECT presensi_absen.* FROM presensi_absen
            LEFT JOIN presensi_karyawan ON presensi_absen.karyawan_id = presensi_karyawan.id
            WHERE presensi_karyawan.instansi_id = %s
            """,
            conn,
            params=[instansi_id],
        )

        conn.close()

    return df_pegawai, df_rencana, df_presensi, df_shift, df_absen


def fetch_via_engine(remote_url: str, instansi_id: int, tanggal_awal: str, tanggal_akhir: str):
    engine = get_engine(remote_url)
    with engine.connect() as conn:
        df_pegawai = pd.read_sql_query("SELECT * FROM bkd_presensi.presensi_karyawan WHERE instansi_id = %s", conn, params=[instansi_id])

        df_presensi = pd.read_sql_query(
            "SELECT * FROM bkd_presensi.presensi_kehadiran WHERE instansi_id = %s AND date(tanggal_masuk) BETWEEN %s AND %s",
            conn,
            params=[instansi_id, tanggal_awal, tanggal_akhir],
        )

        df_rencana = pd.read_sql_query(
            "SELECT * FROM bkd_presensi.presensi_rencana_shift WHERE instansi_id = %s AND date(tanggal_masuk) BETWEEN %s AND %s",
            conn,
            params=[instansi_id, tanggal_awal, tanggal_akhir],
        )

        df_shift = pd.read_sql_query("SELECT * FROM presensi_shift", conn)

        # presensi_absen may not have instansi_id column; filter using joined presensi_karyawan
        df_absen = pd.read_sql_query(
            "SELECT presensi_absen.* FROM presensi_absen LEFT JOIN presensi_karyawan ON presensi_absen.karyawan_id = presensi_karyawan.id WHERE presensi_karyawan.instansi_id = %s",
            conn,
            params=[instansi_id],
        )

    return df_pegawai, df_rencana, df_presensi, df_shift, df_absen


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--instansi', type=int, required=True)
    p.add_argument('--month', type=int, required=True)
    p.add_argument('--year', type=int, required=True)
    p.add_argument('--remote-url', default=os.getenv('REMOTE_DATABASE_URL'))
    p.add_argument('--local-url', default=os.getenv('DATABASE_URL'))
    p.add_argument('--use-ssh', action='store_true')
    p.add_argument('--ssh-host')
    p.add_argument('--ssh-port', type=int, default=22)
    p.add_argument('--ssh-user')
    p.add_argument('--ssh-password')
    p.add_argument('--db-host', default='127.0.0.1')
    p.add_argument('--db-port', type=int, default=3306)
    p.add_argument('--db-user')
    p.add_argument('--db-password')
    p.add_argument('--db-name', default='bkd_presensi')
    p.add_argument('--out-table', default='rekap_kehadiran')
    p.add_argument('--out-excel', default=None)
    p.add_argument('--save-raw', action='store_true', help='Save raw fetched tables (presensi_karyawan, presensi_rencana_shift, presensi_kehadiran, presensi_shift, presensi_absen) to local DB')
    p.add_argument('--replace-raw', action='store_true', help='When saving raw tables, replace existing local tables instead of appending')
    args = p.parse_args()

    # compose tanggal_awal / akhir
    from calendar import monthrange
    tanggal_awal = f"{args.year}{args.month:02d}01"
    tanggal_akhir = f"{args.year}{args.month:02d}{monthrange(args.year, args.month)[1]}"

    tanggal_awal_dt = pd.to_datetime(tanggal_awal)
    tanggal_akhir_dt = pd.to_datetime(tanggal_akhir)

    if args.use_ssh:
        # ensure required SSH args
        ssh_host = args.ssh_host or os.getenv('SSH_HOST')
        ssh_user = args.ssh_user or os.getenv('SSH_USER')
        ssh_password = args.ssh_password or os.getenv('SSH_PASSWORD')
        db_user = args.db_user or os.getenv('DB_USER')
        db_password = args.db_password or os.getenv('DB_PASSWORD')
        if not all([ssh_host, ssh_user, db_user, db_password]):
            print('When using --use-ssh you must pass --ssh-host, --ssh-user and database credentials (or set corresponding env vars)')
            return

        df_pegawai, df_rencana, df_presensi, df_shift, df_absen = fetch_via_ssh(
            ssh_host,
            args.ssh_port,
            ssh_user,
            ssh_password,
            args.db_host,
            args.db_port,
            db_user,
            db_password,
            args.db_name,
            args.instansi,
            tanggal_awal_dt.strftime('%Y-%m-%d'),
            tanggal_akhir_dt.strftime('%Y-%m-%d'),
        )
    else:
        remote = args.remote_url
        if not remote:
            print('No remote DB URL provided. Set REMOTE_DATABASE_URL or pass --remote-url')
            return
        df_pegawai, df_rencana, df_presensi, df_shift, df_absen = fetch_via_engine(remote, args.instansi, tanggal_awal_dt.strftime('%Y-%m-%d'), tanggal_akhir_dt.strftime('%Y-%m-%d'))

    # merge rencana + shift similar to notebook
    df_rencana_shift = df_rencana.merge(df_shift, left_on='shift_id', right_on='id')

    # convert and normalize columns similar to notebook (safe coercions)
    for col in ['tanggal_masuk']:
        if col in df_rencana_shift.columns:
            df_rencana_shift[col] = pd.to_datetime(df_rencana_shift[col])

    # combine date + time columns if present (the notebook used additions)
    # Attempt to add time offsets if columns exist
    for time_col in ['masuk_pre_time', 'masuk_post_time', 'masuk_max_time', 'pulang_pre_time', 'pulang_post_time', 'jam_masuk', 'jam_pulang']:
        if time_col in df_rencana_shift.columns:
            try:
                df_rencana_shift[time_col] = df_rencana_shift['tanggal_masuk'] + pd.to_timedelta(df_rencana_shift[time_col])
            except Exception:
                # fallback: try direct to_datetime (some columns already have full datetimes)
                df_rencana_shift[time_col] = pd.to_datetime(df_rencana_shift[time_col], errors='coerce')

    # ensure absences dates are datetimes
    if 'tanggal_mulai' in df_absen.columns:
        df_absen['tanggal_mulai'] = pd.to_datetime(df_absen['tanggal_mulai'])
    if 'tanggal_selesai' in df_absen.columns:
        df_absen['tanggal_selesai'] = pd.to_datetime(df_absen['tanggal_selesai'])

    # ensure presensi datetimes are parsed
    if 'tanggal_masuk' in df_presensi.columns:
        df_presensi['tanggal_masuk'] = pd.to_datetime(df_presensi['tanggal_masuk'])
    if 'tanggal_kirim' in df_presensi.columns:
        df_presensi['tanggal_kirim'] = pd.to_datetime(df_presensi['tanggal_kirim'])

    # generate laporan
    df_laporan = generate_presensi_laporan(df_pegawai, df_rencana_shift, df_presensi, df_absen, args.month, args.year, tanggal_awal_dt, tanggal_akhir_dt)

    # post-process: merge names from pegawai if available
    if 'id' in df_pegawai.columns and 'name' in df_pegawai.columns and 'nip' in df_pegawai.columns:
        df_laporan = df_laporan.merge(df_pegawai[['id', 'nip', 'name']], left_on='karyawan_id', right_on='id', how='left', suffixes=('', '_pegawai'))

    # write to local DB
    local = args.local_url
    if not local:
        print('No local DATABASE_URL provided. Set DATABASE_URL or pass --local-url')
        return

    local_engine = get_engine(local)

    # Optionally save raw fetched tables to the local DB
    if args.save_raw:
        mode = 'replace' if args.replace_raw else 'append'
        try:
            print(f"Saving raw tables to local DB (mode={mode})...")
            df_pegawai.to_sql('presensi_karyawan', local_engine, if_exists=mode, index=False, method='multi')
            df_rencana.to_sql('presensi_rencana_shift', local_engine, if_exists=mode, index=False, method='multi')
            df_presensi.to_sql('presensi_kehadiran', local_engine, if_exists=mode, index=False, method='multi')
            df_shift.to_sql('presensi_shift', local_engine, if_exists=mode, index=False, method='multi')
            df_absen.to_sql('presensi_absen', local_engine, if_exists=mode, index=False, method='multi')
            print('Saved raw tables to local DB')
        except Exception as e:
            print('Failed to save raw tables to local DB:', e)
            # continue to try writing laporan as well

    df_laporan.to_sql(args.out_table, local_engine, if_exists='replace', index=False, method='multi')
    print(f'Wrote {len(df_laporan)} rows to local table {args.out_table}')

    # prepare output folder and excel path
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    if args.out_excel:
        # If user provided a path and it's absolute, respect it. If it's a
        # relative filename, place it under the `out/` folder to keep outputs
        # organized.
        candidate = Path(args.out_excel)
        if candidate.is_absolute():
            out_path = candidate
        else:
            out_path = out_dir / candidate
    else:
        # default organized path
        out_path = out_dir / f"rekap_{args.instansi}_{args.month}_{args.year}.xlsx"

    df_laporan.to_excel(out_path, index=False)
    print(f'Wrote Excel report to {out_path}')


if __name__ == '__main__':
    main()
