import sqlite3
import random
from datetime import datetime

db = sqlite3.connect("ihlaller.db")
imlec = db.cursor()

imlec.execute(
    """
    CREATE TABLE IF NOT EXISTS ihlaller(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zaman TEXT,
        kisi_id TEXT,
        tur TEXT,
        sure INTEGER,
        durum TEXT        
    )    
    """    
)

for i in range(50):
    kisi_id = random.choice(["Kişi1", "Kişi2", "Kişi3", "Kişi4", "Kişi5"])
    tur = random.choice(["goz_kapali", "hareketsiz"])
    sure = random.randint(2, 15)
    durum = random.choice(["aktif", "pasif"])
    saat = random.randint(1, 19)
    dakika = random.randint(5, 59)
    zaman = f"2026-03-17 {saat}:{dakika}"
    imlec.execute("INSERT INTO ihlaller (zaman, kisi_id, tur, sure, durum) VALUES (?, ?, ?, ?, ?)", (zaman, kisi_id, tur, sure, durum))

db.commit()
db.close()
    
    