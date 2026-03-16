import os
import requests
import cv2
import io
import time
import threading
from dotenv import load_dotenv

class TelegramBotu:
    def __init__(self, token=None, chat_id=None):
        self.son_mesaj_zamani = 0
        self.bekleme_suresi = 30
        load_dotenv()
        if token is not None:
            self.token = token
        else:
            self.token = os.getenv("TOKEN") 
        
        if chat_id is not None:
            self.chat_id = chat_id
        else:
            self.chat_id = os.getenv("CHAT_ID")           
        
        if not self.token:
            self.aktif =False
        else:
            self.aktif = True    
    
    def _gonderebilir_mi(self):
        su_an = time.time()
        
        if su_an - self.son_mesaj_zamani >= self.bekleme_suresi:
            self.son_mesaj_zamani = su_an
            return True
        
        else:
            return False            
    
    def mesaj_gonder(self, metin):
        if self.aktif == False:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            veri = {"chat_id": self.chat_id, "text": metin, "parse_modu":"Markdown"}
            requests.post(url, data=veri, timeout=10)
        except Exception as e:
            print("Mesaj gönderilemedi: ", e)
    
    def foto_gonder(self, frame, aciklama=""):
        if self.aktif == False:
            return
        
        try: 
            _, buffer = cv2.imencode(".jpg", frame)
            bio = io.BytesIO(buffer)
            bio.name = "test.jpg"
            
            url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
            dosyalar = {"photo":bio}
            veriler = {"chat_id":self.chat_id, "caption":aciklama}
            requests.post(url, data=veriler, files=dosyalar, timeout=10)
        except Exception as e:
            print("HATA: Fotoğraf Gönderilemedi: ", e)                  
    
    def ihlal_bildir(self, kisi_id, ihlal_turu, sure, frame=None):
        if not self._gonderebilir_mi():
            return
            
        t = threading.Thread(
            target=self._gonder,
            args=(kisi_id, ihlal_turu, sure, frame),
            daemon=True
        )
        t.start()

    def _gonder(self, kisi_id, ihlal_turu, sure, frame=None):
        if self.aktif == False:
            return
            
        rapor_metni = f"""
        *GÜVENLİK İHLALİ*
        
        Kişi ID: {kisi_id}
        İhlal Türü: {ihlal_turu}
        Süre: {sure}
        """
        
        if frame is not None:
            self.foto_gonder(frame, aciklama=rapor_metni)
        else:
            self.mesaj_gonder(rapor_metni)
      
    
    def sistem_durumu(self, aktif_kisi, toplam_ihlal):
        if self.aktif == False:
            return
        metin = f"""
        *Sistem Aktif*
        
        Anlık İzlenen: {aktif_kisi} kişi
        Toplam İhlal: {toplam_ihlal}
        """    
        self.mesaj_gonder(metin)    
    
    def gun_sonu_raporu(self, istatistikler):
        if self.aktif == False:
            return
        mesaj = f"""
        *GÜNLÜK ÇALIŞMA RAPORU*
        Toplam Tespit Edilen: {istatistikler.get('toplam_insan', 0)}
        Engellenen İhlal: {istatistikler.get('ihlal_sayisi', 0)}
        """        
        self.mesaj_gonder(mesaj)

if __name__ == "__main__":
    bot = TelegramBotu()
    # bot.mesaj_gonder("Sistem başladı.MERHABA")
    # bot.sistem_durumu(aktif_kisi=2, toplam_ihlal=5)
    # bot.ihlal_bildir(kisi_id=100, ihlal_turu="Hareketsizlik", sure=10)
    # veriler = {
    #     "toplam_insan": 150,
    #     "ihlal_sayisi": 12
    # }
    # bot.gun_sonu_raporu(veriler)        
    
    bot.bekleme_suresi = 5
    print(f"Her mesaj arası en az {bot.bekleme_suresi} saniye olmalı.\n")
    
    for i in range(1,6):
        print(f"Deneme {i} bildirim gönderilmeye çalışılıyor...")
        
        bot.ihlal_bildir(kisi_id=i, ihlal_turu="Test", sure=3)
        if i < 5:
            time.sleep(3)
            