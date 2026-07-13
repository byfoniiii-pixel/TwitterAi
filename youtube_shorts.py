from flask import Flask, redirect, url_for, request
import os
import time
import random
import threading
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests
from urllib.parse import quote
import pickle

app = Flask(__name__)

TELEGRAM_CHANNEL = "t.me/sila_mysli_bot"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_quotes():
    return [
        "Every morning is a fresh start. Make it count! 💪",
        "Success is built one day at a time. Keep going! 🔥",
        "Your only limit is you. Break free! ⭐",
        "Dream it. Believe it. Achieve it. 🎯",
        "Hard work beats talent. Stay disciplined! 💎",
        "The comeback is always stronger than the setback. 💪",
        "Don't stop until you're proud. Keep pushing! 🚀",
        "Your future self is watching. Make them proud! 💡",
        "Small progress is still progress. Keep moving! ",
        "You are capable of amazing things. Believe! ✨"
    ]

def download_background():
    themes = [
        "mountain sunrise motivational aesthetic vertical 9:16",
        "ocean waves sunset peaceful vertical shorts",
        "forest path sunlight inspiring vertical",
        "city night lights success vertical video",
        "desert sunset dramatic motivation vertical",
        "space stars galaxy inspiration vertical",
        "waterfall nature power vertical shorts",
        "beach paradise dream vertical",
        "autumn leaves golden growth vertical",
        "northern lights aurora magic vertical"
    ]
    theme = random.choice(themes)
    encoded = quote(theme)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={random.randint(1, 99999)}"
    response = requests.get(url)
    filename = f"background_{int(time.time())}.jpg"
    with open(filename, 'wb') as f:
        f.write(response.content)
    return filename

def create_text_image(quote):
    img = Image.new('RGB', (1080, 1920), color='black')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    words = quote.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(' '.join(current_line)) > 30:
            lines.append(' '.join(current_line[:-1]))
            current_line = [word]
    lines.append(' '.join(current_line))
    y_position = 650
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x_position = (1080 - text_width) // 2
        draw.text((x_position+4, y_position+4), line, fill='#1a1a1a', font=font)
        draw.text((x_position, y_position), line, fill='white', font=font)
        y_position += 90
    link_text = f"👉 More: {TELEGRAM_CHANNEL}"
    bbox = draw.textbbox((0, 0), link_text, font=small_font)
    text_width = bbox[2] - bbox[0]
    x_position = (1080 - text_width) // 2
    draw.text((x_position, 1650), link_text, fill='#FF0000', font=small_font)
    filename = f"text_{int(time.time())}.jpg"
    img.save(filename)
    return filename

def create_short_video():
    print("🎬 Создаю YouTube Short...")
    quote = random.choice(get_quotes())
    print(f"Цитата: {quote}")
    background_path = download_background()
    text_path = create_text_image(quote)
    try:
        clip = ImageClip(background_path).set_duration(15)
        text_clip = ImageClip(text_path).set_duration(15)
        text_clip = text_clip.crossfadein(1)
        final_video = CompositeVideoClip([clip, text_clip.set_pos('center')])
        final_video = final_video.set_fps(30)
        output_file = f"short_{int(time.time())}.mp4"
        final_video.write_videofile(output_file, fps=30, codec='libx264', audio=False, verbose=False, logger=None)
        print(f"✅ Видео создано: {output_file}")
        os.remove(background_path)
        os.remove(text_path)
        return output_file, quote
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None, None

def upload_to_youtube(video_file, title, description):
    try:
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                print("⚠️ Нужно авторизоваться в YouTube")
                return False
        youtube = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["motivation", "success", "mindset", "inspiration", "shorts"],
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        }
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        response = request.next_chunk()
        print(f"✅ Видео загружено на YouTube! ID: {response[1]['id']}")
        os.remove(video_file)
        return True
    except HttpError as e:
        print(f"❌ YouTube API ошибка: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return False

def auto_post_shorts():
    while True:
        try:
            print(f"\n🕐 {datetime.now()} - Создаю новый Short...")
            video_file, quote = create_short_video()
            if video_file:
                title = "This Will Change Your Mindset #Shorts"
                description = f"{quote}\n\n👉 Daily motivation: {TELEGRAM_CHANNEL}\n\n#motivation #success #mindset #inspiration #goals #shorts"
                upload_to_youtube(video_file, title, description)
            time.sleep(14400)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(3600)

@app.route('/')
def home():
    return "✅ YouTube Shorts Bot работает! Автопостинг каждые 4 часа."

@app.route('/create', methods=['GET'])
def manual_create():
    video_file, quote = create_short_video()
    if video_file:
        return f"✅ Видео создано: {video_file}<br>Цитата: {quote}"
    else:
        return "❌ Ошибка создания"

@app.route('/auth', methods=['GET'])
def auth_youtube():
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
    return redirect(url_for('home'))

if __name__ == "__main__":
    print("🚀 YouTube Shorts Bot запущен!")
    create_short_video()
    thread = threading.Thread(target=auto_post_shorts, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=8080)
