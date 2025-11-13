import os
from typing import List, Dict, Optional

import pandas as pd
import pymysql
from sqlalchemy import text
from .analytics import get_engine

def analisis_kehadiran(year: int, month: int, minimum_tk: int = 3) -> List[Dict]:
    """
    Run analysis on rekap_bulanan to compute sum of tanpa_keterangan for given year/month.
    """
    
    local_db_connection = pymysql.connect(
        host=os.getenv('DB_HOST_LOCAL', 'localhost'),
        port=int(os.getenv('DB_PORT_LOCAL', 3306)),
        user=os.getenv('DB_USER_LOCAL', 'root'),
        password=os.getenv('DB_PASSWORD_LOCAL', ''),
        db=os.getenv('DB_NAME_LOCAL', 'bkd_presensi')
    )

    df = pd.read_sql("SELECT a.karyawan_id, a1.nip, a1.name as nama_pegawai, a.tahun, sum(a.tanpa_keterangan) as TK FROM bkd_presensi.rekap_bulanan a LEFT JOIN bkd_presensi.presensi_karyawan a1 ON a.karyawan_id = a1.id WHERE 1 AND a.tahun = %s AND a.bulan < %s GROUP BY a.karyawan_id, a.tahun HAVING TK > %s", local_db_connection, params=[year, month, minimum_tk])
    # try:
    #     df = pd.read_sql(sql, local_db_connection, params={"year": year, "month": month})
    # except Exception:
    #     # fallback to executing and fetching rows directly (no pandas)
    #     with local_db_connection.connect() as conn:
    #         res = conn.execute(sql, {"year": year, "month": month})
    #         rows = [dict(r) for r in res.fetchall()]
    #         return rows

    # convert dataframe to list of dict
    return df.to_dict(orient="records")