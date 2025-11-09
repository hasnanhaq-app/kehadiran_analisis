"""Presensi (attendance) transformation functions converted from notebook.

This module contains the core transform logic: helper functions and
`generate_presensi_laporan` which accepts the required DataFrames and
returns a report DataFrame. It's intentionally pure-Pandas so it's easy to
unit-test and reuse from scripts/etl.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

import pandas as pd


def carbon_parse(time_val, add_minutes: int):
    """Shift a datetime-like value by add_minutes and return Timestamp or None."""
    if pd.isna(time_val):
        return None
    t = pd.to_datetime(time_val)
    t = t + pd.Timedelta(minutes=add_minutes)
    return t


def masuk_kategori(row: pd.Series) -> Optional[str]:
    jm, jadwal = row.get('jam_masuk'), row.get('jadwal_masuk')
    if pd.isna(jadwal):
        return None
    if pd.isna(jm):
        return 't4' if not pd.isna(row.get('jam_pulang')) else None
    if jm <= jadwal:
        return 'tw'
    elif jadwal < jm <= carbon_parse(jadwal, 30):
        return 't1'
    elif carbon_parse(jadwal, 30) < jm <= carbon_parse(jadwal, 60):
        return 't2'
    elif carbon_parse(jadwal, 60) < jm <= carbon_parse(jadwal, 90):
        return 't3'
    else:
        return 't4'


def pulang_kategori(row: pd.Series) -> Optional[str]:
    jp, jadwal = row.get('jam_pulang'), row.get('jadwal_pulang')
    if pd.isna(jadwal):
        return None
    if pd.isna(jp):
        return 'p4' if not pd.isna(row.get('jam_masuk')) else None
    if jp >= jadwal:
        return 'tw'
    elif carbon_parse(jadwal, -30) <= jp < jadwal:
        return 'p1'
    elif carbon_parse(jadwal, -60) <= jp < carbon_parse(jadwal, -30):
        return 'p2'
    elif carbon_parse(jadwal, -90) <= jp < carbon_parse(jadwal, -60):
        return 'p3'
    else:
        return 'p4'


def status_hadir(row: pd.Series) -> str:
    if not pd.isna(row.get('jam_masuk')) or not pd.isna(row.get('jam_pulang')):
        return 'hadir'
    elif row.get('keterangan_absen') in ['C', 'S']:
        return 'izin/sakit'
    elif row.get('keterangan_absen') in ['TB', 'BK']:
        return 'tugas/bk'
    else:
        return 'tidak hadir'


def generate_presensi_laporan(df_pegawai: pd.DataFrame, df_rencana: pd.DataFrame, df_presensi: pd.DataFrame, df_absen: pd.DataFrame, bulan_cetak: int, tahun_cetak: int, tanggal_awal, tanggal_akhir) -> pd.DataFrame:
    """Generate the laporan (report) DataFrame from the input tables.

    The function follows the logic imported from the notebook. It expects
    `df_rencana` to already include shift data merged (i.e. rencana+shift) as
    `df_rencana_shift` in the notebook. If not merged, caller should merge
    before calling.
    """
    # Ensure datetime columns are Timestamps for comparisons
    df_rencana = df_rencana.copy()
    df_presensi = df_presensi.copy()
    df_absen = df_absen.copy()

    # Merge karyawan + rencana (inner join)
    df = df_rencana.merge(df_pegawai, left_on='karyawan_id', right_on='id', suffixes=('_r', '_k'))

    laporan_rows = []

    for _, row in df.iterrows():
        karyawan_id = row['karyawan_id']
        instansi_id = row.get('instansi_id_r') or row.get('instansi_id')
        tanggal_kerja = row['tanggal_masuk']
        jadwal_masuk = row.get('masuk_post_time')
        jadwal_pulang = row.get('pulang_pre_time')

        # normalize tanggal_kerja
        tanggal_kerja_ts = pd.Timestamp(tanggal_kerja)
        start_of_day = tanggal_kerja_ts.normalize()
        end_of_day = start_of_day + pd.Timedelta(days=1)

        # Filter absen (izin/cuti) untuk karyawan tsb
        df_absen_karyawan = df_absen[df_absen['karyawan_id'] == karyawan_id]
        absen_row = df_absen_karyawan[(df_absen_karyawan['tanggal_mulai'] <= tanggal_kerja) & (df_absen_karyawan['tanggal_selesai'] >= tanggal_kerja)]

        if not absen_row.empty:
            keterangan_absen = absen_row.iloc[0].get('type')
            jam_masuk = None
            jam_pulang = None
            keterangan_hadir = None
        else:
            df_presensi_karyawan = df_presensi[df_presensi['karyawan_id'] == karyawan_id]

            masuk = df_presensi_karyawan[(df_presensi_karyawan.get('jenis') == 'M') & (df_presensi_karyawan['tanggal_masuk'] >= start_of_day) & (df_presensi_karyawan['tanggal_masuk'] < end_of_day) & (df_presensi_karyawan['approver_status'].isin([None, 'TERIMA']))].sort_values('tanggal_kirim', ascending=True).head(1)

            jam_masuk = masuk['tanggal_kirim'].iloc[0] if not masuk.empty else None

            pulang = df_presensi_karyawan[(df_presensi_karyawan.get('jenis') == 'P') & (df_presensi_karyawan['tanggal_masuk'] >= start_of_day) & (df_presensi_karyawan['tanggal_masuk'] < end_of_day) & (df_presensi_karyawan['approver_status'].isin([None, 'TERIMA']))].sort_values('tanggal_kirim', ascending=False).head(1)

            jam_pulang = pulang['tanggal_kirim'].iloc[0] if not pulang.empty else None

            keterangan_hadir = (
                masuk['catatan'].iloc[0]
                if not masuk.empty and pd.notna(masuk['catatan'].iloc[0])
                else (pulang['catatan'].iloc[0] if not pulang.empty else None)
            )
            keterangan_absen = None

        laporan_rows.append({
            'karyawan_id': karyawan_id,
            'instansi_id': instansi_id,
            'tanggal_kerja': tanggal_kerja,
            'jadwal_masuk': jadwal_masuk,
            'jadwal_pulang': jadwal_pulang,
            'jam_masuk': jam_masuk,
            'jam_pulang': jam_pulang,
            'keterangan_hadir': keterangan_hadir,
            'keterangan_absen': keterangan_absen,
        })

    df_laporan = pd.DataFrame(laporan_rows)
    return df_laporan

def generate_laporan_bulanan(df_laporan: pd.DataFrame) -> pd.DataFrame:
    """Generate monthly report from daily laporan DataFrame."""
    
    df_laporan_bulanan = df_laporan

    df_laporan_bulanan['masuk_kat'] = df_laporan_bulanan.apply(masuk_kategori, axis=1)
    df_laporan_bulanan['pulang_kat'] = df_laporan_bulanan.apply(pulang_kategori, axis=1)
    df_laporan_bulanan['status_hadir'] = df_laporan_bulanan.apply(status_hadir, axis=1)

    # return df_laporan_bulanan

    rekap_per_pegawai = df_laporan_bulanan.groupby(['karyawan_id']).agg(
        jumlah_hari=('tanggal_kerja', 'count'),
        hadir=('status_hadir', lambda x: (x == 'hadir').sum()),
        tidak_hadir=('status_hadir', lambda x: (x != 'hadir').sum()),
        twm=('masuk_kat', lambda x: (x == 'tw').sum()),
        t1=('masuk_kat', lambda x: (x == 't1').sum()),
        t2=('masuk_kat', lambda x: (x == 't2').sum()),
        t3=('masuk_kat', lambda x: (x == 't3').sum()),
        t4=('masuk_kat', lambda x: (x == 't4').sum()),
        twp=('pulang_kat', lambda x: (x == 'tw').sum()),
        p1=('pulang_kat', lambda x: (x == 'p1').sum()),
        p2=('pulang_kat', lambda x: (x == 'p2').sum()),
        p3=('pulang_kat', lambda x: (x == 'p3').sum()),
        p4=('pulang_kat', lambda x: (x == 'p4').sum()),
        izin_sakit=('status_hadir', lambda x: (x == 'izin/sakit').sum()),
        tugas_bk=('status_hadir', lambda x: (x == 'tugas/bk').sum()),
        tanpa_keterangan=('status_hadir', lambda x: (x == 'tidak hadir').sum()),
    ).reset_index()
    
    return rekap_per_pegawai

__all__ = [
    'carbon_parse',
    'masuk_kategori',
    'pulang_kategori',
    'status_hadir',
    'generate_presensi_laporan',
]
