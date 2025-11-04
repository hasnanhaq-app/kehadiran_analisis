import pandas as pd

from app.presensi import (
    carbon_parse,
    masuk_kategori,
    pulang_kategori,
    status_hadir,
    generate_presensi_laporan,
)


def test_carbon_parse():
    t = pd.Timestamp("2025-01-01 08:00:00")
    assert carbon_parse(t, 30) == pd.Timestamp("2025-01-01 08:30:00")
    assert carbon_parse(pd.NaT, 15) is None


def test_masuk_pulang_kategori_and_status():
    # masuk: on-time
    row = pd.Series({"jam_masuk": pd.Timestamp("2025-01-01 08:00:00"), "jadwal_masuk": pd.Timestamp("2025-01-01 08:00:00"), "jam_pulang": pd.NaT})
    assert masuk_kategori(row) == "tw"

    # masuk: 20 minutes late -> t1
    row2 = pd.Series({"jam_masuk": pd.Timestamp("2025-01-01 08:20:00"), "jadwal_masuk": pd.Timestamp("2025-01-01 08:00:00"), "jam_pulang": pd.NaT})
    assert masuk_kategori(row2) == "t1"

    # pulang: on-time
    row3 = pd.Series({"jam_pulang": pd.Timestamp("2025-01-01 17:00:00"), "jadwal_pulang": pd.Timestamp("2025-01-01 17:00:00"), "jam_masuk": pd.NaT})
    assert pulang_kategori(row3) == "tw"

    # status hadir: present when jam_masuk exists
    r = pd.Series({"jam_masuk": pd.Timestamp("2025-01-01 08:00:00"), "jam_pulang": pd.NaT, "keterangan_absen": None})
    assert status_hadir(r) == "hadir"

    # status hadir: izin/sakit when keterangan_absen == 'C'
    r2 = pd.Series({"jam_masuk": pd.NaT, "jam_pulang": pd.NaT, "keterangan_absen": "C"})
    assert status_hadir(r2) == "izin/sakit"


def test_generate_presensi_laporan_basic():
    # Simple scenario: one employee, one rencana, one masuk and one pulang
    df_pegawai = pd.DataFrame([{"id": 1, "nip": "123", "name": "Alice"}])

    df_rencana = pd.DataFrame([
        {
            "karyawan_id": 1,
            "instansi_id": 100,
            "tanggal_masuk": pd.Timestamp("2025-10-01"),
            "masuk_post_time": pd.Timestamp("2025-10-01 08:00:00"),
            "pulang_pre_time": pd.Timestamp("2025-10-01 17:00:00"),
        }
    ])

    df_presensi = pd.DataFrame([
        {
            "karyawan_id": 1,
            "jenis": "M",
            "tanggal_masuk": pd.Timestamp("2025-10-01 08:10:00"),
            "tanggal_kirim": pd.Timestamp("2025-10-01 08:10:00"),
            "approver_status": None,
            "catatan": "",
        },
        {
            "karyawan_id": 1,
            "jenis": "P",
            "tanggal_masuk": pd.Timestamp("2025-10-01 17:05:00"),
            "tanggal_kirim": pd.Timestamp("2025-10-01 17:05:00"),
            "approver_status": None,
            "catatan": "",
        },
    ])

    df_absen = pd.DataFrame(columns=["karyawan_id", "tanggal_mulai", "tanggal_selesai", "type"])

    out = generate_presensi_laporan(
        df_pegawai,
        df_rencana,
        df_presensi,
        df_absen,
        bulan_cetak=10,
        tahun_cetak=2025,
        tanggal_awal=pd.Timestamp("2025-10-01"),
        tanggal_akhir=pd.Timestamp("2025-10-31"),
    )

    assert len(out) == 1
    row = out.iloc[0]
    assert pd.Timestamp(row["jam_masuk"]) == pd.Timestamp("2025-10-01 08:10:00")
    assert pd.Timestamp(row["jam_pulang"]) == pd.Timestamp("2025-10-01 17:05:00")
