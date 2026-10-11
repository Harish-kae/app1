import asyncio
import re
import subprocess
import textwrap
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
IMAGES = ROOT / "images"
OUTPUT = ROOT / "OliVideos"
TEMP = ROOT / "temp_work"
for directory in (IMAGES, OUTPUT, TEMP):
    directory.mkdir(exist_ok=True)

W, H, FPS = 1280, 720, 24

FRUITS = {
    "apple": ("apple.jpg", "https://commons.wikimedia.org/wiki/Special:FilePath/Apple_fruit_1.2.jpg",
              ["apple", "ஆப்பிள்"]),
    "banana": ("banana.jpg", "https://commons.wikimedia.org/wiki/Special:FilePath/Bananas.JPG",
               ["banana", "வாழைப்பழம்", "வாழை"]),
    "mango": ("mango.jpg", "https://commons.wikimedia.org/wiki/Special:FilePath/Mango_(1).jpg",
              ["mango", "மாம்பழம்", "மாம்பழ"]),
    "orange": ("orange.jpg", "https://commons.wikimedia.org/wiki/Special:FilePath/Valencia_orange.jpg",
               ["orange", "ஆரஞ்சு"]),
}

SAMPLE = """வணக்கம் குழந்தைகளே! இன்று நாம் பழங்களைப் பற்றி கற்றுக்கொள்வோம்.
Apple — ஆப்பிள். ஆப்பிள் சிவப்பு அல்லது பச்சை நிறத்தில் இருக்கும்.
Banana — வாழைப்பழம். வாழைப்பழம் மஞ்சள் நிறத்தில் இருக்கும்.
Mango — மாம்பழம். மாம்பழம் இனிப்பான பழம்.
Orange — ஆரஞ்சு. ஆரஞ்சுப் பழத்தில் வைட்டமின் C உள்ளது.
நன்றி குழந்தைகளே! தினமும் பலவகையான பழங்களை சாப்பிடுங்கள்."""

def font(size, bold=False):
    paths = []
    if bold:
        paths += [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\NirmalaB.ttf"]
    paths += [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\Nirmala.ttf"]
    for p in paths:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

def download_images():
    results = []
    headers = {"User-Agent": "OliAIStudio educational video maker"}
    for key, (filename, url, terms) in FRUITS.items():
        path = IMAGES / filename
        if path.exists() and path.stat().st_size > 5000:
            results.append(f"{key}: ready")
            continue
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            if not r.content.startswith(b"\\xff\\xd8") and "image" not in r.headers.get("content-type", "").lower():
                raise ValueError("Download was not an image")
            path.write_bytes(r.content)
            with Image.open(path) as im:
                im.verify()
            results.append(f"{key}: downloaded")
        except Exception as e:
            if path.exists():
                path.unlink(missing_ok=True)
            results.append(f"{key}: unavailable ({e})")
    return results

def fruit_for(text):
    low = text.lower()
    for key, (_, _, terms) in FRUITS.items():
        if any(term.lower() in low for term in terms):
            return key
    return None

def make_frame(text, n, total, fruit):
    img = Image.new("RGB", (W, H), "#FFF8E8")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 25, W-30, H-25), radius=32, fill="white", outline="#F0D49C", width=4)
    d.rounded_rectangle((52, 45, W-52, 130), radius=22, fill="#FFE6A6")
    d.text((80, 64), "Learn with Oli!", font=font(42, True), fill="#55351A")
    d.text((W-170, 76), f"{n}/{total}", font=font(26, True), fill="#55351A")
    d.rounded_rectangle((70, 160, 670, 590), radius=28, fill="#F2F7E9")
    picture = None
    if fruit:
        path = IMAGES / FRUITS[fruit][0]
        try:
            picture = Image.open(path).convert("RGB")
        except Exception:
            pass
    if picture:
        picture = ImageOps.contain(picture, (520, 350), method=Image.Resampling.LANCZOS)
        img.paste(picture, (370-picture.width//2, 370-picture.height//2))
    else:
        # Simple fallback if the internet/photo is unavailable.
        d.ellipse((230, 245, 510, 520), fill="#EF5B55", outline="#B9342E", width=7)
        d.ellipse((300, 290, 360, 350), fill="#FFB5A5")
        d.line((370, 260, 395, 215), fill="#6B4A2D", width=14)
        d.ellipse((390, 205, 465, 240), fill="#4D9A58")
    d.rounded_rectangle((710, 160, 1200, 590), radius=28, fill="#F0F4FF")
    d.text((755, 190), "Let's learn!", font=font(38, True), fill="#263D74")
    lines = textwrap.wrap(re.sub(r"\s+", " ", text), width=29)
    y = 270
    for line in lines[:7]:
        d.text((755, y), line, font=font(25), fill="#273047")
        y += 40
    d.text((80, 625), "Listen, look, and learn!", font=font(27, True), fill="#76522C")
    return img

async def make_audio(text, voice, path):
    await edge_tts.Communicate(text=text, voice=voice, rate="-5%").save(str(path))

def ffmpeg(args):
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.run([exe, "-y", "-hide_banner", "-loglevel", "error"] + args,
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-2500:] or "FFmpeg failed.")

def scene_video(image, audio, output):
    ffmpeg(["-loop", "1", "-framerate", str(FPS), "-i", str(image), "-i", str(audio),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(output)])

def join_videos(paths, output):
    listing = TEMP / "concat_list.txt"
    with listing.open("w", encoding="utf-8") as f:
        for p in paths:
            f.write("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
            "-movflags", "+faststart", str(output)])

st.set_page_config(page_title="Oli AI Studio", page_icon="🦉", layout="wide")
st.title("🦉 Oli AI Studio")
st.write("Make a narrated learning video using Tamil voices and real fruit photos.")

with st.sidebar:
    st.header("Video settings")
    choice = st.selectbox("Narrator", ["Female — Tamil", "Male — Tamil", "Female — Indian English"])
    voice = {
        "Female — Tamil": "ta-IN-PallaviNeural",
        "Male — Tamil": "ta-IN-ValluvarNeural",
        "Female — Indian English": "en-IN-NeerjaNeural",
    }[choice]
    title = st.text_input("Video title", "Learn Fruits in Tamil")

st.subheader("1. Your narration")
st.caption("Write one scene per line. The app makes one video scene for each line.")
script = st.text_area("Narration text", value=SAMPLE, height=230)
st.caption("Mention apple, banana, mango or orange (English or Tamil) in a line to show that fruit's photo.")

if st.button("🖼️ Download / check fruit photos"):
    with st.spinner("Checking image files..."):
        for result in download_images():
            st.write("• " + result)

st.divider()
if st.button("🎬 Generate MP4 video", type="primary", use_container_width=True):
    scenes = [s.strip() for s in script.splitlines() if s.strip()]
    if not scenes:
        st.error("Enter at least one scene.")
    else:
        with st.spinner("Checking fruit images..."):
            image_results = download_images()
        st.write("Photo check:", " | ".join(image_results))
        progress = st.progress(0)
        status = st.empty()
        clips = []
        try:
            for i, line in enumerate(scenes, start=1):
                status.write(f"Creating scene {i} of {len(scenes)}...")
                png = TEMP / f"scene_{i:03d}.png"
                mp3 = TEMP / f"scene_{i:03d}.mp3"
                mp4 = TEMP / f"scene_{i:03d}.mp4"
                make_frame(line, i, len(scenes), fruit_for(line)).save(png)
                asyncio.run(make_audio(line, voice, mp3))
                scene_video(png, mp3, mp4)
                clips.append(mp4)
                progress.progress(i / len(scenes))
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "Oli_Lesson"
            output = OUTPUT / f"{safe}.mp4"
            join_videos(clips, output)
            status.success("Video complete!")
            st.video(str(output))
            st.success(f"Saved to: {output}")
        except Exception as e:
            st.error("The video could not be completed.")
            st.code(str(e))
            st.info("Check your internet connection and install packages with: py -m pip install streamlit edge-tts imageio-ffmpeg pillow requests")
