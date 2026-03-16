#İnternet üzerinden veri alıp göndermemizi(HTTP istekleri) sağlayan kütüphane
import requests 
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# def mesaj_gonder(metin): #İçine yazılan metni işleyecek bir fonksiyon oluşturduk
#     #Mesajın gideceği tam web adresini bot şifremizle birleştirerek oluşturduk
#     url = f"https://api.telegram.org/bot{TOKEN}/sendMessage" 
    
#     # Paketi hazırlıyoruz: Kime gidecek(chat_id) ve içinde ne yazacak(text)
#     veri = {"chat_id": CHAT_ID, "text": metin} 
    
#     # Postacıya(requests) paketi verip Telegram'ın adresine yolluyoruz
#     yanit = requests.post(url, data=veri)
    
#     #Eğer Telegramdan gelen cevap kodu 200 ise (İnternet dilinde 200 başarılı demektir.)
#     if yanit.status_code == 200:
#         #Terminal ekranına mesajın başarıyla gittiğini yazdırdık.
#         print("Mesaj gönderildi.") 
#     else: # Eğer cevap 200 dışında birşeyse(404,400 gibi hatalar fln.)
#         print(f"HATA: {yanit.status_code}") #Terminal ekranına hatanın numarasını yazdırıyoruz.

# mesaj_gonder("GuardWatch başlatıldı! Sistem aktif.")        



def ihlal_bildirimi(kisi_id, ihlal_turu, sure):
    metin = (
        "*GuardWatch İhlal*\n\n"
        f"Kişi ID: {kisi_id}\n"
        f"Tür: {ihlal_turu}\n"
        f"Süre: {sure:.1f} saniye\n"
        f"Zaman: {datetime.now().strftime('%H:%M:%S')}"
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    #Parse mode: Markdown kısmı yazıyı şekillendirmemizi sağlıyor
    veri = {"chat_id": CHAT_ID, "text": metin, "parse_mode": "Markdown"}
    return requests.post(url, data=veri)
ihlal_bildirimi(1, "Göz Kapalı", 20.1458)    

    
