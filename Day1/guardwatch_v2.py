import sys  # Programı güvenli kapatmak için (exit)
import os  # Dosya var mı yok mu kontrol etmek için
import math
import csv
import cv2
import json
from ultralytics import YOLO
import threading
import winsound
import os
import argparse
import mediapipe as mp
import matplotlib.pyplot as plt
import time
import pygame
import logging
from datetime import datetime
from gun1_telegram import TelegramBotu
import shutil  # Klasörleri içindeki yüzlerce hatta binlerce dosya ile birlikte tek hamlede siler


telegram = TelegramBotu()

try:
    logging.basicConfig(
        filename="guvenlik.log", level=logging.INFO, format="%(asctime)s - %(message)s"
    )  # Log dosyamızın ayarlarını yapıyoruz.(Tarih - Mesaj formatında yazacak)
    logging.info("Sistem basladi")  # Sistem çalışır çalışmaz ilk kaydımızı düşüyoruz
except PermissionError:
    print("UYARI: 'guvenlik.log' dosyası başka bir programda açık!")
    print("Loglama devre dışı bırakıldı,ancak program çalışmaya devam edecek.")
    logging.basicConfig(level=logging.CRITICAL)
loglanmis_ihlaller = (
    {}
)  # İhlallerin dosyaya saniyede 30 kez yazılmasını engellemek için hafıza sözlüğü
pygame.mixer.init()  # Pygame'in ses motorunu başlatıyoruz (Bunu yapmazsak ses çalışmaz)
try:
    alarm_sesi = pygame.mixer.Sound(
        "beep.wav"
    )  # Alarmı dosya koduna yükleyip alarm_sesi adını veriyoruz
except FileNotFoundError:
    print("UYARI: 'beep.wav' dosyası bulunamadı! Sesli uyarı çalışmayacak.")
    alarm_sesi = None

son_alarm_zamani = 0.0
csv_dosya = "ihlaller.csv"

parser = argparse.ArgumentParser(description="GuardWatch AI Güvenlik Sistemi")
parser.add_argument(
    "--kaynak", type=str, default="0", help="Video dosyasının yolu ve kamera ID'si"
)
parser.add_argument(
    "--kayit",
    action="store_true",
    help="İhlalleri CSV dosyasına kaydetmeyi aktif eder.",
)
komutlar = parser.parse_args()

video_kaynagi = komutlar.kaynak
kayit_aktif_mi = komutlar.kayit

if kayit_aktif_mi:
    if not os.path.exists(csv_dosya):
        with open(csv_dosya, "w", newline="") as dosya:
            yaz = csv.writer(dosya)
            yaz.writerow(
                [
                    "zaman",
                    "kisi_id",
                    "ihlal_turu",
                    "sure_sn",
                    "ear_degeri",
                    "frame_yolu",
                ]
            )
        print(
            "[BİLGİ] 'ihlaller.csv' dosyası başlıklarla birlikte sıfırdan oluşturuldu."
        )
    else:
        print(
            "[BİLGİ] Mevcut 'ihlaller.csv' dosyası bulundu,kayıtlara buradan devam edilecek."
        )
else:
    print(
        "[BİLGİ] '--kayit' komutu verilmedi.İhlaller sadece ekranda görünecek,CSV'ye kaydedilmeyecek."
    )


def ayarları_yukle(dosya_yolu="config.json"):
    gerekli_anahtarlar = [
        "ear_threshold",
        "goz_kapali_limit_sn",
        "hareketsizlik_limit_sn",
        "hareket_piksel_esigi",
        "yolo_confidence",
        "tracker_max_mesafe",
    ]
    print(f"Ayarlar '{dosya_yolu}' dosyasından okunuyor...")

    if not os.path.exists(
        dosya_yolu
    ):  # os.path.exists Dosya fiziksel olarak orada mı bakıyor
        print(f"KRITIK HATA: '{dosya_yolu}' dosyası bilgisayarda bulunamadı!!!")
        print("ÇÖZÜM: Lütfen proje klasörüne bu dosyayı ekleyin...")
        sys.exit(1)  # Programı HATA koduyla (1) anında kapatır.
    try:
        with open(dosya_yolu, "r") as f:
            yuklenen_ayarlar = json.load(f)
            eksik_var_mi = False
            for anahtar in gerekli_anahtarlar:
                if anahtar not in yuklenen_ayarlar:
                    print(
                        f"HATA: Config dosyasında '{anahtar}' ayarı yazılmamış/silinmiş!"
                    )
                    eksik_var_mi = True
            if eksik_var_mi:
                print("Lütfen yukarıdaki eksik ayarları config.json dosyasına ekleyin.")
                sys.exit(
                    1
                )  # Eksik ayarlarla program çalışırsa ileride çöker.O yüzden şuan kapatıyoruz.
            print("BASARILI: Tüm ayarlar tam ve doğru formatta")
            return yuklenen_ayarlar
    except json.JSONDecodeError:  # Yazım hataları var mı ona bakar parantez virgül fln.
        print(f"KRITIK HATA: '{dosya_yolu}' dosyası BOZUK!")
        print("İPUCU: Dosyadaki virgülleri,tırnakları ve parantezleri kontrol edin.")
        sys.exit(1)  # Bozuk dosya ile çalışamayız.
    except Exception as e:
        print(f"BEKLENMEDİK BİR HATA OLUŞTU: {e}")
        sys.exit(1)


CONFIG = ayarları_yukle()

try:
    model = YOLO("yolov8n.pt")
    print("BASARILI: YOLO modeli hafızaya alındı.")
except Exception as hata_mesaji:
    print("KRİTİK HATA: Yapay zeka modeli yüklenemedi!")
    print(f"Teknik Hata Detayı: {hata_mesaji}")
    print("---------------------------")
    print("ÇÖZÜM ÖNERİLERİ:")
    print(
        "1. 'yolov8n.pt' dosyasının projenin olduğu klasörde bulunduğundan emin olun."
    )
    print("2. Dosya adının doğru yazıldığını kontrol edin.")
    print("3. Ultralytics kütüphanesinin yüklü olduğundan emin olun.")
    sys.exit(1)  # Model yoksa program çalışmaz bir anlamı kalmaz!

if video_kaynagi != "0" and not os.path.exists(video_kaynagi):
    print(f"HATA: Belirtilen video dosyası bulunamadı: {video_kaynagi}")
    print("ÇÖZÜM: Dosya adını yanlış yazmış olabilirsiniz veya dosya silinmiş.")
    sys.exit(1)
print(f"Görüntü kaynağına ({video_kaynagi}) bağlanılıyor...")

if video_kaynagi == "0":
    kamera = cv2.VideoCapture(0)
else:
    kamera = cv2.VideoCapture(video_kaynagi)

if not kamera.isOpened():  # Kamera başarıyla açıldı mı diye kontrol ediyoruz
    print("HATA: Kamera veya Video açılamadı!")
    if video_kaynagi == "0":
        print(
            "İPUCU: Webcam takılı mı? Başka bir program (Zoom,Discord) kamerayı kullanıyor olabilir."
        )
    sys.exit(1)

uyku_zamanlayicilari = {}  # Hangi ID'nin saat kaçtan beri uyuduğunu tutacağımız hafıza

son_bilinen_konumlar = (
    {}
)  # Hangi ID'nin en son hangi (x,y) koordinatında olduğunu tutar
hareketsizlik_zamanlayicilari = (
    {}
)  # Hangi ID'nin saat kaçtan beri yerinden kıpırdamadığını tutar

mp_face_mesh = mp.solutions.face_mesh  # MediaPipe Face Mesh modelini hazırlıyoruz
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=10, refine_landmarks=True
)  # refine landmarks ayarı gözleri daha hassas taramasını sağlar


def resim_kaydet_thread(kopyalanmis_frame, dosya_yolu):
    cv2.imwrite(dosya_yolu, kopyalanmis_frame)
    print(f"[THREAD] Fotoğraf arka planda kaydedildi: {dosya_yolu}")


alarm_caliniyor = False


def alarm_cal():
    global alarm_caliniyor
    if alarm_caliniyor:
        return
    alarm_caliniyor = True
    print("[THREAD] ALARM ÇALIYOR! (Kamera donmadan arka planda)")
    # 1000Hz frekansında 2000 ms (2 saniye) boyunca bip sesi çıkar
    winsound.Beep(1000, 2000)
    alarm_caliniyor = False


def eski_kayitlari_temizle(klasor_yolu="kayitlar/2026-03-06", gun_limit=7):
    print(f"\n--------- GUARDWATCH OTOMATİK TEMİZLİK SİSTEMİ BAŞLADI -------")
    if not os.path.exists(
        klasor_yolu
    ):  # Program ilk kez çalışıyorsa "kayitlar" klasörü hiç yoktur.Hata vermemesi için return ile fonksiyonu anında bitirip geri döndürüyoruz
        print("[BİLGİ] Kayıtlar klasörü henüz oluşturulmamış, temizlik atlandı.")
        return
    simdi = time.time()
    silinen_klasor_sayisi = 0

    for klasör_adi in os.listdir(
        klasor_yolu
    ):  # "kayitlar" klasörünün içindeki herşeye sırayla bak
        tam_yol = os.path.join(klasor_yolu, klasör_adi)
        if os.path.isdir(tam_yol):  # Sadece klasörlerle ilgilen
            try:
                datetime.strptime(klasör_adi, "%Y-%m-%d")
                klasor_zamani = os.path.getmtime(tam_yol)
                yas_gun = (simdi - klasor_zamani) / 86400

                if yas_gun > gun_limit:
                    shutil.rmtree(
                        tam_yol
                    )  # Klasörü içindeki yüzlerce fotoğrafla beraber tek hamlede siler
                    silinen_klasor_sayisi += 1
                    print(
                        f"SİLİNDİ: {klasör_adi} klasörü ({yas_gun:.1f} günlük çöp temizlendi.)"
                    )
            except ValueError:
                continue
    if silinen_klasor_sayisi > 0:
        print(
            f"[BİLGİ] GuardWatch Temizliği tamamlandı. {silinen_klasor_sayisi} adet eski klasör imha edildi."
        )


def ihlal_frame_kaydet(frame, kisi_id, ear_degeri, sure_sn=0.0):
    if sure_sn > 10.0:
        klasor_adi = "arsiv"  # Silinmeyecek olan GÜVENLİ Klasör
    else:
        # 10 saniyeden kısaysa , silinmek üzere bugünün tarihli klasörüne at
        klasor_adi = datetime.now().strftime("%Y-%m-%d")

    klasor_yolu = os.path.join(
        "kayitlar", klasor_adi
    )  # Yolu birleştirip klasörü oluşturuyoruz
    os.makedirs(klasor_yolu, exist_ok=True)
    tam_zaman = datetime.now().strftime("%H-%M-%S")
    dosya_adi = f"ihlal_{kisi_id}_{tam_zaman}.jpg"
    tam_kayit_yolu = os.path.join(klasor_yolu, dosya_adi)
    print(f"Hazırlanan kayıt yolu: {tam_kayit_yolu}")

    bilgi_metni = f"EAR: {ear_degeri:.3f} | Kisi: {kisi_id} | Sure: {sure_sn:.1f} sn"
    cv2.putText(
        frame, bilgi_metni, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
    )
    t_kayit = threading.Thread(
        target=resim_kaydet_thread, args=(frame.copy(), tam_kayit_yolu)
    )
    t_kayit.start()
    return tam_kayit_yolu


def gun_sonu_raporu(dosya_adi):
    print("\n--- GuardWatch Derin Analiz Raporu Hazırlanıyor... ---")

    try:
        with open(dosya_adi, "r", newline="") as f:
            okuyucu = list(csv.DictReader(f))
            toplam_kayit = len(okuyucu)
            if toplam_kayit == 0:
                print("Henüz kaydedilmiş bir veri bulunamadı.")
                return
            en_uzun_ihlal = 0
            toplam_ear = 0
            kisi_sayimi = {}
            tur_sayimi = {}

            for satir in okuyucu:
                if satir.get("sure_sn") is None or satir.get("ear_degeri") is None:
                    continue
                    print(
                        "EĞER TERMİNALDE BU YAZIYI GÖRÜYORSAN CONTINUE İŞE YARAMIYOR DEMEKTİR!"
                    )
                    # 1. En Uzun Süreyi Bulma
                sure = float(satir["sure_sn"])
                if sure > en_uzun_ihlal:
                    en_uzun_ihlal = sure

                # 2. EAR Ortalaması İçin Toplama
                toplam_ear += float(satir["ear_degeri"])

                # 3. Kişi Bazlı Sayım (Sözlük Mantığı)
                k_id = satir["kisi_id"]
                kisi_sayimi[k_id] = kisi_sayimi.get(k_id, 0) + 1

                # 4. Tür Bazlı Sayım
                t_id = satir["ihlal_turu"]
                tur_sayimi[t_id] = tur_sayimi.get(t_id, 0) + 1

            print(f" TOPLAM İHLAL: {toplam_kayit}")
            print(f" EN UZUN UYKU/HAREKETSİZLİK: {en_uzun_ihlal:.2f} sn")
            print(f" ORTALAMA EAR: {toplam_ear/toplam_kayit:.3f}")
            print("-" * 20)
            print(f" KİŞİ BAŞI: {kisi_sayimi}")
            print(f" TÜR BAŞI : {tur_sayimi}")
            telegram_istatistikleri = {
                "toplam_insan": len(kisi_sayimi),
                "ihlal_sayisi": toplam_kayit
            }
            telegram.gun_sonu_raporu(telegram_istatistikleri)
    except FileNotFoundError:
        print(
            f"HATA: '{dosya_adi}' dosyası bulunamadı.Henüz ihlal yapılmamış olabilir."
        )
    except KeyError as e:
        print(f"HATA: CSV dosyasındaki sütun isimleri uyuşmuyor! Eksik alan: {e}")
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")


def grafikleri_ciz(dosya_adi):
    print("\n---- Grafikler Oluşturuluyor... ----")

    kisi_sayaci = {}
    saat_sayaci = {}

    try:
        with open(dosya_adi, "r", newline="", encoding="utf-8") as dosya:
            oku = csv.reader(dosya)
            baslik = next(oku)

            for satir in oku:
                kisi = "Kisi_" + str(satir[1])

                if kisi in kisi_sayaci:
                    kisi_sayaci[kisi] += 1
                else:
                    kisi_sayaci[kisi] = 1
                zaman_metni = satir[0]
                saat_kismi = zaman_metni.split(" ")[1]
                saat = saat_kismi.split(":")[0]

                if saat in saat_sayaci:
                    saat_sayaci[saat] += 1
                else:
                    saat_sayaci[saat] = 1
        print("[BİLGİ] CSV verileri başarıyla okundu ve sayıldı!")

        kisi_isimleri = list(kisi_sayaci.keys())
        kisi_ihlal_sayilari = list(kisi_sayaci.values())

        sirali_saatler = sorted(saat_sayaci.keys())
        saat_ihlal_sayilari = []

        for s in sirali_saatler:
            saat_ihlal_sayilari.append(saat_sayaci[s])
        if len(kisi_isimleri) > 0:
            plt.figure(figsize=(8, 5))
            plt.bar(kisi_isimleri, kisi_ihlal_sayilari, color="steelblue")

            plt.title("Kişi Bazlı Toplam İhlal Sayısı")
            plt.xlabel("Kişiler")
            plt.ylabel("İhlal Sayısı")
            plt.savefig("kisi_bazli_ihlal.png", dpi=150, bbox_inches="tight")
            plt.close()
            print("[BİLGİ] 'kisi_bazli_ihlal.png' başarıyla kaydedildi.")
        if len(sirali_saatler) > 0:
            plt.figure(figsize=(10, 5))
            plt.plot(
                sirali_saatler,
                saat_ihlal_sayilari,
                marker="o",
                color="crimson",
                linewidth=2,
            )
            plt.title("Saatlik İhlal Dağılımı")
            plt.xlabel("Saat Dilimi")
            plt.ylabel("İhlal Sayısı")
            plt.grid(True, alpha=0.3)
            plt.savefig("saatlik_ihlal_dagilimi.png", dpi=150, bbox_inches="tight")
            plt.close()
            print("[BİLGİ] 'saatlik_ihlal_dagilimi.png' başarıyla kaydedildi.")
    except FileNotFoundError:
        print(f"HATA: Grafik çizmek için '{dosya_adi}' bulunamadı.")
    except Exception as e:
        print(f"HATA: Grafik verileri okunurken bir sorun oluştu: {e}")


def ihlal_kaydet(
    kisi_id, ihlal_turu, sure, ear, frame=None
):  # Kişi uyuduğunda yada hareketsiz kaldığında bu fonksiyon çağrılır
    # Gelen verileri alıp 'ihlaller.csv' dosyasının en alt satırına ekler.
    if not kayit_aktif_mi:
        return
    zaman = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )  # Bugünün saati ve tarihini aldık
    frame_yolu = ""

    if frame is not None:  # Eğer fonksiyona bir fotoğraf (frame) gönderildiyse
        frame_yolu = ihlal_frame_kaydet(
            frame, kisi_id, ear, sure
        )  # Fotoğrafı kaydet ve geri dönen dosya adresini 'frame_yolu' değişkenine eşitle

    with open(
        "ihlaller.csv", "a", newline=""
    ) as dosya:  # Tüm verileri (fotoğraf yolu da dahil) CSV'ye tek seferde yaz
        yaz = csv.writer(dosya)
        sure_metni = f"{sure:.2f}"
        ear_metni = f"{ear:.3f}" if ear is not None else "0.000"
        yaz.writerow([zaman, kisi_id, ihlal_turu, sure_metni, ear_metni, frame_yolu])


def oklid_hesapla(p1, p2):
    fark_x = p2[0] - p1[0]
    fark_y = p2[1] - p1[1]

    toplam = (fark_x**2) + (fark_y**2)
    karekok = math.sqrt(toplam)
    return karekok


def ear_hesapla(goz_koordinatlari):
    p1 = goz_koordinatlari[0]  # Sol Köşe
    p2 = goz_koordinatlari[1]  # Sol Üst
    p3 = goz_koordinatlari[2]  # Sağ Üst
    p4 = goz_koordinatlari[3]  # Sağ Köşe
    p5 = goz_koordinatlari[4]  # Sağ Alt
    p6 = goz_koordinatlari[5]  # Sol Alt

    sol_dik = oklid_hesapla(p2, p6)
    sag_dik = oklid_hesapla(p3, p5)
    yatay = oklid_hesapla(p1, p4)

    ear_degeri = (sol_dik + sag_dik) / (2 * yatay)
    return ear_degeri


def merkez_hesapla(kutu):
    # kutu[0] = x1    kutu[1] = y1  kutu[2] = x2  kutu[3] = y2

    merkez_x = int((kutu[0] + kutu[2]) / 2)
    merkez_y = int((kutu[1] + kutu[3]) / 2)
    return (merkez_x, merkez_y)


takip_listesi = (
    {}
)  # Ekranda takip ettiğimiz kişilerin merkez noktalarını tutacağımız boş sözlük
siradaki_id = 0  # Yeni tespit edilen kişilere vereceğimiz ilk ID


def tracker_guncelle(yeni_merkezler):
    global siradaki_id, takip_listesi  # Dışarıda tanımladığımız id değişkenini içeride değiştirebilmek için izin alıyoz
    guncel_takip = (
        {}
    )  # Sadece bu framede ekranda olan kişileri tutacağımız geçici liste

    for (
        yeni_m
    ) in (
        yeni_merkezler
    ):  # YOLO'nun bulduğu her bir yeni merkez noktası için sırayla dönüyoruz
        eslesti_mi = False  # Başlangıçta bu yeni merkezin eski biriyle eşleşmediğini varsayıyoruz

        for (
            obje_id,
            eski_m,
        ) in (
            takip_listesi.items()
        ):  # Hafızadaki(önceki karedeki) kayıtlı ID'leri ve onların eski merkezlerini kontrol ediyoruz
            mesafe = oklid_hesapla(
                yeni_m, eski_m
            )  # Yeni bulduğumuz nokta ile hafızadaki eski nokta arasındaki mesafeyi ölçüyoruz

            if (
                mesafe < CONFIG["tracker_max_mesafe"]
            ):  # Eğer aralarındaki mesafe configdeki sınırımızdan küçükse
                guncel_takip[obje_id] = (
                    yeni_m  # BU aynı kişi ID'sini koruyup yeni merkez koordinatını kaydediyoruz
                )
                eslesti_mi = True  # Eşleşme sağlandığı için durumu True yapıyoruz
                break  # Bu kişi ile işimiz bitti hafızadaki diğer eski kişilere bakmaya gerek yok döngüden çık
        if (
            not eslesti_mi
        ):  # Eğer hafızadaki kimseyle eşleşmediyse (mesafe hep büyük çıktıysa veya hafıza boşsa)
            guncel_takip[siradaki_id] = (
                yeni_m  # Bu yepyeni birisi.Ona sıradaki boş ID'yi veriyoruz ve merkezini kaydediyoruz
            )
            siradaki_id += 1  # Bir sonraki yeni kişi için ID sayacını 1 arttırıyoruz(0 ise 1 , 1 ise 2)
    takip_listesi.clear()  # Ana hafızamızı(eski listeyi) tamamen temizliyoruz ki ekrandan çıkanlar silinsin
    takip_listesi.update(
        guncel_takip
    )  # Sadece bu karede eşleştirdiğimiz ve yeni eklediğimiz kişileri (taze listeyi) ana hafızaya yazıyoruz
    return takip_listesi  # Güncellenmiş takip listesini ana döngüde kullanmak üzere geri gönderiyoruz


def yolo_kutulari_bul(
    frame,
):  # Görüntüdeki nesnelerin kutu koordinatlarını bulur ve liste olarak döndürür
    bulunan_kutular = (
        []
    )  # YOLO'nun bulacağı kutuları içine atacağımız boş bir liste oluşturuyoruz
    sonuclar = model(
        frame, verbose=False
    )  # Görüntüyü YOLO modeline verip sonuçları alıyoruz(verbose=False ekrana gereksiz log yazmasını engeller)
    for sonuc in sonuclar:  # YOLO'dan gelen sonuçların içinde sırayla geziniyoruz
        for (
            kutu
        ) in (
            sonuc.boxes
        ):  # O sonucun içindeki her bir dikdörtgen kutuya tek tek bakıyoruz
            guven_skoru = float(
                kutu.conf[0]
            )  # Yapay zekanın bu kutudaki nesneden yüzde kaç emin olduğunu alıyoruz
            if (
                guven_skoru > CONFIG["yolo_confidence"]
            ):  # Eğer güven skoru bizim configdeki eşiğimizden büyükse bu kutuyu kabul ediyoruz
                x1, y1, x2, y2 = map(
                    int, kutu.xyxy[0]
                )  # Kutunun 4 köşesinin koordinatlarını tam sayı olarak alıyoruz
                genislik = x2 - x1
                yeni_y1 = (
                    y1  # Üst (y1) alt (y2) sınırları YOLO'nun bulduğu gibi bırakıyoruz.
                )
                yeni_y2 = y2  # Böylece kutu kafadan başlar ve bacaklara/ayaklara kadar uzanır.

                yeni_x1 = x1 + int(
                    genislik * 0.32
                )  # Sol kenarı (x1) toplam genişliğin %32'si kadar sağa itiyoruz
                yeni_x2 = x2 - int(
                    genislik * 0.32
                )  # Sağ kenarı (x2) toplam genişliğin %32'si kadar sola itiyoruz
                bulunan_kutular.append(
                    [yeni_x1, yeni_y1, yeni_x2, yeni_y2]
                )  # Koordinatları bir liste yapıp,ana listemize ekliyoruz
    return bulunan_kutular  # Bulduğumuz tüm geçerli kutuların listesini dışarıya gönderiyoruz


def kare_isle(frame):  # Bir fotoğrafı alır,işler,üzerine çizim yapıp geri döndürür.
    global son_alarm_zamani  # Dışarıda tanımladığımız alarm sayacını içeride değiştirebilmek için izin alıyoruz

    try:
        kutular = yolo_kutulari_bul(frame)  # Resimdeki tüm kutuları alıyoruz
        merkezler = []  # Merkez noktalarını tutacağımız boş bir liste hazırlıyoruz
        rgb_frame = cv2.cvtColor(
            frame, cv2.COLOR_BGR2RGB
        )  # Görüntüyü RGB formatına çeviriyoruz
        ear_degeri, burun_merkezi = uyku_durumu_bul(rgb_frame)  # Ear Değerini alıyoruz
        for kutu in kutular:  # YOLO'nun bulduğu her bir kutu için döngüye giriyoruz
            cv2.rectangle(frame, (kutu[0], kutu[1]), (kutu[2], kutu[3]), (255, 0, 0), 2)
            merkez_noktasi = merkez_hesapla(kutu)  # Kutunun tam ortasını buluyoruz
            merkezler.append(
                merkez_noktasi
            )  # Bulduğumuz bu merkez noktasını listemize ekliyoruz
        aktif_kisiler = tracker_guncelle(
            merkezler
        )  # Merkez noktalarını Trackera gönderip güncel ID'leri alıyoruz
        genel_tehlike_durumu = False  # Bütün kişileri kontrol etmeden önce genel tehlike durumunu Yok(False) sayıyoruz
        for (
            k_id,
            k_merkez,
        ) in (
            aktif_kisiler.items()
        ):  # Ekranda aktif olan her bir kişi için çizim yapmaya başlıyoruz
            goz_tehlikede = False
            hareket_tehlikede = False
            cv2.circle(
                frame, k_merkez, 5, (0, 0, 255), -1
            )  # Kişinin tam merkez noktasına küçük kırmızı bir nokta çiziyoruz

            if (
                ear_degeri is not None
            ):  # Eğer MediaPipe bir yüz veya göz bulabildiyse hesaplamaya başla
                if (
                    ear_degeri < CONFIG["ear_threshold"]
                ):  # Göz kapalıysa EAR değeri CONFİG de ki eşiğimizden küçük mü?
                    if (
                        k_id not in uyku_zamanlayicilari
                    ):  # Bu kişi hafızada yoksa yani gözünü ilk defa tam şuanda kapattıysa
                        uyku_zamanlayicilari[k_id] = (
                            time.time()
                        )  # Şuanki saati/saniyeyi al ve bu kişinin ID'siyle hafızaya kaydet Kronometreyi başlat
                    else:  # Bu kişi zaten hafızada varsa yani gözü bir süredir kapalıysa
                        gecen_sure = (
                            time.time() - uyku_zamanlayicilari[k_id]
                        )  # Şuanki zamandan gözünü ilk kapattığı zamanı çıkar
                        if (
                            gecen_sure > CONFIG["goz_kapali_limit_sn"]
                        ):  # Eğer geçen süre configde ki limitten (2.0 sn) büyükse
                            genel_tehlike_durumu = (
                                True  # Biri uyuduğu için tehlike bayrağını kaldır
                            )
                            goz_tehlikede = True

                            if (
                                loglanmis_ihlaller.get(f"{k_id}_uyku") != True
                            ):  # Eğer bu adamın uykusunu daha önce dosyaya YAZMADIYSAK
                                logging.info(
                                    f"IHLAL BASLADİ (ID={k_id},tur = goz_kapali)"
                                )
                                loglanmis_ihlaller[f"{k_id}_uyku"] = (
                                    True  # Artık yazıldı olarak işaretle
                                )
                                ihlal_kaydet(k_id, "goz_kapali", gecen_sure, ear_degeri)
                                ihlal_kaydet(
                                    k_id, "goz_kapali", gecen_sure, ear_degeri, frame
                                )
                                telegram.ihlal_bildir(kisi_id=k_id, ihlal_turu="Göz Kapalı", sure=gecen_sure, frame=frame)
                            if (
                                gecen_sure >= 10.0
                                and loglanmis_ihlaller.get(f"{k_id}_uyku_arsiv") != True
                            ):
                                print(
                                    f"[KRİTİK UYARI] ID={k_id} 10 saniyeden uzun süredir uyuyor! Arşive kanıt alınıyor."
                                )
                                ihlal_kaydet(
                                    k_id, "kritik_uyku", gecen_sure, ear_degeri, frame
                                )
                                loglanmis_ihlaller[f"{k_id}_uyku_arsiv"] = True
                                telegram.ihlal_bildir(kisi_id=k_id, ihlal_turu="KRİTİK UYKU", sure=gecen_sure, frame=frame)
                else:  # Göz Açıksa EAR değeri eşikten büyükse
                    if k_id in uyku_zamanlayicilari:
                        del uyku_zamanlayicilari[
                            k_id
                        ]  # Göz açıldığı an tehlike geçmiştir.Bu kişinin kaydını hafızadan sil (Kronometreyi sıfırla)

                        if (
                            loglanmis_ihlaller.get(f"{k_id}_uyku") == True
                        ):  # Bu adamın uyuduğunu daha önce log'a bildirmiş miydik
                            logging.info(f"IHLAL BITTI (ID = {k_id},tur=goz_kapali)")
                            loglanmis_ihlaller[f"{k_id}_uyku"] = False

                if burun_merkezi is not None:
                    takip_noktasi = burun_merkezi
                else:
                    takip_noktasi = k_merkez

                cv2.circle(frame, takip_noktasi, 5, (0, 255, 0), -1)
                if k_id in son_bilinen_konumlar:
                    hareket_miktari = oklid_hesapla(
                        takip_noktasi, son_bilinen_konumlar[k_id]
                    )

                    if hareket_miktari < CONFIG["hareket_piksel_esigi"]:
                        if k_id not in hareketsizlik_zamanlayicilari:
                            hareketsizlik_zamanlayicilari[k_id] = time.time()
                        else:
                            gecen_hareketsiz_sure = (
                                time.time() - hareketsizlik_zamanlayicilari[k_id]
                            )
                            if gecen_hareketsiz_sure > CONFIG["hareketsizlik_limit_sn"]:
                                genel_tehlike_durumu = True
                                hareket_tehlikede = True
                                if loglanmis_ihlaller.get(f"{k_id}_hareketsiz") != True:
                                    logging.info(
                                        f"IHLAL BASLADI (ID = {k_id},tur =hareketsiz)"
                                    )
                                    loglanmis_ihlaller[f"{k_id}_hareketsiz"] = True
                                    guvenli_ear = (
                                        ear_degeri if ear_degeri is not None else 0.0
                                    )
                                    ihlal_kaydet(
                                        k_id,
                                        "hareketsiz",
                                        gecen_hareketsiz_sure,
                                        guvenli_ear,
                                        frame,
                                    )
                                    telegram.ihlal_bildir(kisi_id=k_id, ihlal_turu="Hareketsizlik", sure=gecen_hareketsiz_sure, frame=frame)
                                if (
                                    gecen_hareketsiz_sure >= 10.0
                                    and loglanmis_ihlaller.get(
                                        f"{k_id}_hareketsiz_arsiv"
                                    )
                                    != True
                                ):
                                    print(
                                        f"[KRİTİK UYARI] ID={k_id} 10 saniyeden uzun süredir hareketsiz! Arşive kanıt alınıyor."
                                    )
                                    guvenli_ear = (
                                        ear_degeri if ear_degeri is not None else 0.0
                                    )
                                    ihlal_kaydet(
                                        k_id,
                                        "kritik_hareketsiz",
                                        gecen_hareketsiz_sure,
                                        guvenli_ear,
                                        frame,
                                    )
                                    loglanmis_ihlaller[f"{k_id}_hareketsiz_arsiv"] = (
                                        True
                                    )
                                    telegram.ihlal_bildir(kisi_id=k_id, ihlal_turu="KRİTİK HAREKETSIZLIK", sure=gecen_hareketsiz_sure, frame=frame)
                    else:
                        son_bilinen_konumlar[k_id] = takip_noktasi
                        if k_id in hareketsizlik_zamanlayicilari:
                            del hareketsizlik_zamanlayicilari[k_id]
                            if loglanmis_ihlaller.get(f"{k_id}_hareketsiz") == True:
                                logging.info(
                                    f"IHLAL BITTI (ID = {k_id},tur = hareketsiz)"
                                )
                                loglanmis_ihlaller[f"{k_id}_hareketsiz"] = False
                else:
                    son_bilinen_konumlar[k_id] = takip_noktasi
                    logging.info(f"Kisi tespit edildi ( ID = {k_id})")

            if goz_tehlikede and hareket_tehlikede:
                cv2.putText(
                    frame,
                    "UYKU IHLALI",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    3,
                )
            elif goz_tehlikede:
                cv2.putText(
                    frame,
                    "GOZ KAPALI",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 255),
                    3,
                )
            elif hareket_tehlikede and ear_degeri is not None:
                cv2.putText(
                    frame,
                    "HAREKETSIZ",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 255),
                    3,
                )
            else:
                cv2.putText(
                    frame,
                    "NORMAL",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )
        if (
            genel_tehlike_durumu == True and ear_degeri is not None
        ):  # Bütün kişiler kontrol edildikten sonra bayrağın son durumuna bakıyoruz
            if not alarm_caliniyor:
                t_alarm = threading.Thread(
                    target=alarm_cal, daemon=True
                )  # Daemon True ise na program yani kamera aniden kapanırsa bunlarda kapancak işi bırakcak
                t_alarm.start()
    except Exception as e:
        print(f"UYARI: Kare işlenirken hata oluştu: {e}")
    return frame  # İşlemleri biten ve üzerine çizim yapılan resmi geri gönderiyoruz


def uyku_durumu_bul(
    rgb_frame,
):  # MediaPipe ile göz noktalarını bulur ve EAR değerini hesaplayıp döndürür
    sonuclar = face_mesh.process(
        rgb_frame
    )  # Resmi MediaPipe'a veriyoruz ve yüz noktalarını taramasını istiyoruz
    if (
        not sonuclar.multi_face_landmarks
    ):  # Eğer ekranda hiçbir yüz bulamadıysa işlem yapmadan None döndürüyoruz
        return None, None
    yuz_noktalari = sonuclar.multi_face_landmarks[
        0
    ].landmark  # Ekranda yüz varsa ilk bulduğu yüzün noktalarını alıyoruz
    sol_goz_indeksleri = [
        33,
        160,
        158,
        133,
        153,
        144,
    ]  # Sol gözün etrafındaki 6 noktanın MediaPipedaki sabit numaraları
    h, w, _ = (
        rgb_frame.shape
    )  # Resmin yüksekliğini ve genişliğini alıyoruz ki noktaları piksele çevirebilelim
    goz_koordinatlari = (
        []
    )  # Göz koordinatlarını biriktireceğimiz boş bir liste açıyoruz
    for i in sol_goz_indeksleri:  # Sadece sol gözün 6 noktası için döngüye giriyoruz
        nokta = yuz_noktalari[i]  # Haritadan o numaralı noktayı alıyoruz
        x_piksel = int(nokta.x * w)
        y_piksel = int(
            nokta.y * h
        )  # Noktalar 0 ile 1 arasında gelir.Bunu resmin eni ve boyuyla çarpıp tam sayı (piksel) yapıyoruz
        goz_koordinatlari.append(
            (x_piksel, y_piksel)
        )  # Bulduğumuz piksel koordinatını listeye ekliyoruz
    ear_degeri = ear_hesapla(
        goz_koordinatlari
    )  # Bulduğumuz bu 6 noktayı ear_hesapla fonksiyonuna gönderip EAR değerini alıyoruz
    burun_noktasi = yuz_noktalari[1]
    burun_x = int(burun_noktasi.x * w)
    burun_y = int(burun_noktasi.y * h)
    burun_merkezi = (burun_x, burun_y)
    return (
        ear_degeri,
        burun_merkezi,
    )  # Hesaplanan EAR değerini ve burnun nerede olduğunu geri gönderiyoruz


def main():  # Kamerayı başlatır,görüntüleri okur ve işleyerek ekranda gösterir.
    print("GuardWatch Başladı... Çıkmak için klavyeden 'q' tuşuna basın.")
    while True:  # Sonsuz bir döngü başlatıyoruz
        ret, frame = kamera.read()
        if not ret:  # Eğer fotoğraf okunamadıysa döngüyü kırıp çıkıyoruz
            print("Kameradan görüntü alınamıyor.Kapatılıyor...")
            break

        islenmis_frame = kare_isle(
            frame
        )  # Okuduğumuz ham fotoğrafı,o yazdığımız dev fonksiyona yollayıp işlenmiş halini alıyoruz
        cv2.imshow(
            "GuardWatch Kamera", islenmis_frame
        )  # Üzerine kutular ve yazılar çizilmiş olan bu yeni fotoğrafı ekranda gösteriyoruz
        if cv2.waitKey(1) & 0xFF == ord(
            "q"
        ):  # Klavyeyi dinle 1 milisaniye bekle ve basılan tuş 'q' ise döngüyü bitir
            break

    kamera.release()  # Döngü bitince kamerayı donanımsal olarak serbest bırakıyoruz
    cv2.destroyAllWindows()  # Ekranda açık kalan tüm OpenCV pencerelerini temizleyip kapatıyoruz


if (
    __name__ == "__main__"
):  # Eğer bu dosya (guardwatch.py) doğrudan çalıştırıldıysa main() fonksiyonunu tetikle
    try:
        eski_kayitlari_temizle(
            gun_limit=7
        )  # Kamera açılmadan hemen önce eski klasörleri limite göre temizle!
        main()  # Ana fonksiyonu çalıştır
        gun_sonu_raporu(csv_dosya)
        grafikleri_ciz(csv_dosya)
    except KeyboardInterrupt:
        # Kullanıcı terminalde CTRL+C yaparak programı durdurmaya veya kapatmaya çalışırsa burası çalışacak
        print("BİLGİ: Program kullanıcı tarafından (CTRL + C) durduruldu.")
        gun_sonu_raporu(csv_dosya)
        grafikleri_ciz(csv_dosya)
        print("Çıkış yapılıyor....")
        if "kamera" in globals() and kamera.isOpened():
            kamera.release()
        cv2.destroyAllWindows()
        sys.exit(0)  # Başarıyla isteyerek çıktım.Hata yok demektir.

print("\n GUARDWATCH başarıyla sonlandırıldı.")
