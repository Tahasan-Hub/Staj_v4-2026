import requests
import cv2
import io #Giriş/Çıkış işlemleri kütüphanesi.Pc hafızasında sanal işlemler yapmamızı sağlar.
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# def foto_gonder(foto_yolu, aciklama=""):
#     url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
#     with open(foto_yolu, "rb") as foto: # rb(read binary) bu bir metin değil resim dosyası onu pc dilinde oku demektir.
#         #Telegrama  al bu senin fotoğraf dosyan  demek için dosyayı paketledik
#         dosyalar = {"photo": foto}
#         veri = {"chat_id": CHAT_ID, "caption":aciklama} #Fotolarda text yerine caption kullanılır
        
#         #Postacıya(requests) hem yazılı veriyi hem de fotoğraf dosyasını verip Telegrama yolluyoruz.
#         yanit = requests.post(url, data=veri, files=dosyalar)
#     return yanit.status_code == 200 
#     #Eğer Telegram 200 başarılı derse kod çalıştığı yere True demezse False bilgisini gönderir.

# foto_gonder(r"C:\Users\tahas\OneDrive\Desktop\guardwatch_v2\Day6\kayitlar\2026-03-09\ihlal_0_00-32-13.jpg", "Orada bir insan var.")        


def frame_gonder(frame, aciklama=""): #YOLO'nun o an yakaladığı frame'i alıp gönderecek fonksiyonu tanımladık.
    _, buffer = cv2.imencode('.jpg', frame) #Kameradan gelen o görüntüyü hafıza içinde(RAM'de) anında .jpg formatına dönüştürüp sıkıştırıyoruz(buffer)
    bio = io.BytesIO(buffer) # Sıkıştırdığımız bu veriyi alıp, hafızada sanki gerçek bir dosyaymış gibi davranan sanal bir pakete(bio) koyuyoruz
    bio.name = "ihlal.jpg" #Telegram bu veriyi kabul etsin diye bu sanal dosyaya uydurma bir isim veriyoruz
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    dosyalar = {"photo": bio} #Hazırladığımız o sanal dosyayı kargo paketine koyuyoruz
    veri = {"chat_id": CHAT_ID, "caption": aciklama} 
    return requests.post(url, data=veri, files=dosyalar)

        