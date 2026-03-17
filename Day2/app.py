from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


app = Flask(__name__)

def db_baglan():
    db = sqlite3.connect("ihlaller.db")
    db.row_factory = sqlite3.Row
    return db

@app.route("/ihlaller")
def ihlaller():
    db=db_baglan()
    kisi = request.args.get("kisi")
    tur = request.args.get("tur")
    sayfa = int(request.args.get("sayfa", default=1))
    sorgu = "SELECT * FROM ihlaller WHERE 1=1"
    params = []
    limit = 20
    offset = (sayfa - 1) * limit
    if kisi:
        sorgu += " AND kisi_id = ?"
        params.append(kisi)
    if tur:
        sorgu += " AND ihlal_turu = ?"
        params.append(tur)   
    sorgu += f" ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])      
    veriler = db.execute(sorgu, params).fetchall()
    tum_kisiler = db.execute("SELECT DISTINCT kisi_id FROM ihlaller").fetchall()
    db.close()
    return render_template("ihlaller.html", ihlaller=veriler, sayfa=sayfa, kisiler = tum_kisiler, secili_kisi=kisi, secili_tur = tur)


@app.route("/grafikler")
def grafikler_sayfasi():
    db = db_baglan()
    os.makedirs("static/grafikler", exist_ok=True)
    kisi_verileri = db.execute("SELECT kisi_id, COUNT(*) as sayi FROM ihlaller GROUP BY kisi_id").fetchall()
    kisiler = [f"Kişi {row['kisi_id']}"  for row in kisi_verileri]
    sayilar = [row['sayi'] for row in kisi_verileri]
    
    if sayilar:
        max_ihlal = max(sayilar)
        renkler = ['red' if sayi == max_ihlal else 'skyblue' for sayi in sayilar]
    else:
        renkler = []
    
    plt.figure(figsize=(8, 5))
    plt.bar(kisiler, sayilar, color=renkler)
    plt.title("Kişilere Göre İhlal Sayıları", fontsize=14, fontweight='bold')
    plt.xlabel("Kişiler")
    plt.ylabel("Toplam İhlal Sayısı")
    plt.savefig("static/grafikler/kisi_bar.png")
    plt.close()
    
    saat_verileri = db.execute("SELECT SUBSTR(zaman, 1, 2) as saat, COUNT(*) as sayi FROM ihlaller GROUP BY saat ORDER BY saat").fetchall()
    saatler = [f"{row['saat']}:00" for row in saat_verileri]
    saat_sayilar = [row['sayi'] for row in saat_verileri]

    plt.figure(figsize=(8, 5))
    plt.plot(saatler, saat_sayilar, marker='o', color='green', linestyle='-', linewidth=2)
    plt.title("Saatlere Göre İhlal Yoğunluğu", fontsize=14, fontweight='bold')
    plt.xlabel("Günün Saatleri")
    plt.ylabel("İhlal Sayısı")      
    plt.grid(True, linestyle='--', alpha=0.6) 
    plt.savefig("static/grafikler/saatlik_line.png")
    plt.close()  
    tur_verileri = db.execute("SELECT ihlal_turu, COUNT(*) as sayi FROM ihlaller GROUP BY ihlal_turu").fetchall()
    
    turler = [row['ihlal_turu'].replace('_', ' ').title() for row in tur_verileri]
    tur_sayilar = [row['sayi'] for row in tur_verileri]

    plt.figure(figsize=(6, 6))
    plt.pie(tur_sayilar, labels=turler, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff'])
    plt.title("İhlal Türü Dağılımı", fontsize=14, fontweight='bold')
    plt.savefig("static/grafikler/tur_pie.png")
    plt.close()

    db.close()
    return render_template("grafikler.html")


@app.route("/api/durum")
def api_durum():
    db = db_baglan()
    toplam = db.execute("SELECT COUNT(*) FROM ihlaller").fetchone()[0]
    kisi_sayisi = db.execute("SELECT COUNT(DISTINCT kisi_id) FROM ihlaller").fetchone()[0]
    db.close()
    
    return jsonify({
        "sistem": "aktif",
        "toplam_ihlal": toplam,
        "kisi_sayisi": kisi_sayisi,
        "son_guncelleme": datetime.now().isoformat()
    })

@app.route("/api/ihlaller")
def api_ihlaller():
    db = db_baglan()
    kisi = request.args.get("kisi")
    tur = request.args.get("tur")
    limit = int(request.args.get("limit", 10))
    
    sorgu = "SELECT * FROM ihlaller WHERE 1=1"
    params = []
    
    if kisi:
        sorgu += " AND kisi_id = ?"
        params.append(kisi)
    if tur:
        sorgu += " AND ihlal_turu = ?"
        params.append(tur)
        
    sorgu += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    satirlar = db.execute(sorgu, params).fetchall()
    db.close()
    
    veriler = [dict(satir) for satir in satirlar]
    
    return jsonify({
        "kayit_sayisi": len(veriler),
        "ihlaller": veriler
    })


@app.route("/kisi/<int:kisi_id>")
def kisi_detay(kisi_id):
    db = db_baglan()
    ihlaller = db.execute(
        "SELECT * FROM ihlaller WHERE kisi_id = ? ORDER BY id DESC",
        (kisi_id,)
    ).fetchall()
    if len(ihlaller) > 0:
        istatistik = db.execute(
            "SELECT AVG(sure), MAX(sure) FROM ihlaller WHERE kisi_id = ?",
            (kisi_id,)
        ).fetchone()
        en_sik_sorgu = db.execute(
            "SELECT ihlal_turu FROM ihlaller WHERE kisi_id = ? GROUP BY ihlal_turu ORDER BY COUNT(*) DESC LIMIT 1",
            (kisi_id,)
        ).fetchone()
        toplam = len(ihlaller)
        ortalama = round(istatistik[0], 2) 
        en_uzun = istatistik[1]
        en_sik = en_sik_sorgu[0]
        son_zaman = ihlaller[0]['zaman'] 
    else:
        toplam, ortalama, en_uzun, en_sik, son_zaman = 0, 0, 0, "Yok", "-"
    
    db.close()
    return render_template(
        "kisi_detay.html",
        kisi_id=kisi_id,
        ihlaller=ihlaller,
        toplam=toplam,
        ortalama=ortalama,
        en_uzun=en_uzun,
        en_sik=en_sik,
        son_zaman=son_zaman
    )

@app.route("/")
def anasayfa():
    db = db_baglan()
    
    toplam = db.execute("SELECT COUNT(*) FROM ihlaller").fetchone()[0]
    son_10 = db.execute("SELECT * FROM ihlaller ORDER BY id DESC LIMIT 10").fetchall()
    aktif = db.execute("SELECT COUNT(*) FROM ihlaller WHERE durum = 'aktif'").fetchone()[0]
    kisi_sayisi = db.execute("SELECT COUNT(DISTINCT kisi_id) FROM ihlaller").fetchone()[0]
    su_an = datetime.now().strftime("%H:%M:%S")
    db.close()
    
    return render_template("anasayfa.html", toplam_ihlal=toplam, son_ihlaller=son_10, aktif_ihlal = aktif, izlenen_kisi = kisi_sayisi, son_guncelleme = su_an)

if __name__ == "__main__":
    app.run(debug=True, port=5000)