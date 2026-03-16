import cv2
import io
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

kamera = cv2.VideoCapture(0)
ret, frame = kamera.read()
cv2.putText(frame, su_an, (40,40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0),3)

_, buffer = cv2.imencode('.jpg', frame)
bio = io.BytesIO(buffer)
bio.name = "test.jpg"

url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
dosya = {"photo": bio}
veri = {"chat_id":CHAT_ID, "caption": "İşte anlık görüntü"}

requests.post(url, data=veri, files=dosya)

kamera.release()
