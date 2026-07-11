
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import DB_CONFIG

import firebirdsql
import time

start_time = time.time()
conn = firebirdsql.connect(
            **DB_CONFIG,
        )
cur = conn.cursor()

sql_string = f"select WFLARTIKELNUMMER, ARTIKELNUMMER, ZEICHNUNGSNUMMER, MATCHCODE, DISPONENT from ARTIKELSTAMMDATEN WHERE MANDANT = 1 AND GESPERRT = 0"  # GESPERRT, AKTIV = 1 bedeutet nicht gesperrte Artikel, verringert Laufzeit von 1,4 auf 0,4 Sekunden TODO SUM über GESPERRT für Live-Änderungen
cur.execute(sql_string)
rows=cur.fetchall()
for c in rows:
    print(c)
print(len(rows))
print("%0.8f Sekunden: Daten aus ARTIKELSTAMMDATEN" % (time.time() - start_time))
