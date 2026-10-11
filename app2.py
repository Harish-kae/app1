import os
import re
import math
import asyncio
import subprocess
import tempfile
import wave
from pathlib import Path

import streamlit as st
import edge_tts
import imageio
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont


# ---------- APP SETTINGS ----------

st.set_page_config(page_title="Oli AI Studio 2.0", page_icon="🦉", layout="centered")
st.title("🦉 Oli AI Studio 2.0")
st.write("Create colourful Tamil-learning cartoons for children with Oli!")

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "OliVideos"
VIDEO_DIR.mkdir(exist_ok=True)

LESSONS = {
    "fruits": [
        ("Apple", "ஆப்பிள்", "Aappil", "apple"),
        ("Banana", "வாழைப்பழம்", "Vaazhaipazham", "banana"),
        ("Mango", "மாம்பழம்", "Maampazham", "mango"),
        ("Orange", "ஆரஞ்சு", "Aaranju", "orange"),
    ],
    "animals": [
        ("Cat", "பூனை", "Poonai", "cat"),
        ("Dog", "நாய்", "Naai", "dog"),
        ("Cow", "பசு", "Pasu", "cow"),
        ("Elephant", "யானை", "Yaanai", "elephant"),
    ],
    "colors": [
        ("Red", "சிவப்பு", "Sivappu", "red"),
        ("Blue", "நீலம்", "Neelam", "blue"),
        ("Green", "பச்சை", "Pachai", "green"),
        ("Yellow", "மஞ்சள்", "Manjal", "yellow"),
    ],
    "numbers": [
        ("One", "ஒன்று", "Ondru", "one"),
        ("Two", "இரண்டு", "Irandu", "two"),
        ("Three", "மூன்று", "Moondru", "three"),
        ("Four", "நான்கு", "Naangu", "four"),
    ],
    "greetings": [
        ("Hello", "வணக்கம்", "Vanakkam", "hello"),
        ("Thank you", "நன்றி", "Nandri", "thank you"),
        ("Come", "வா", "Vaa", "come"),
        ("Go", "போ", "Poo", "go"),
    ],
    "family": [
        ("Mother", "அம்மா", "Amma", "mother"),
        ("Father", "அப்பா", "Appa", "father"),
        ("Older brother", "அண்ணா", "Anna", "brother"),
        ("Older sister", "அக்கா", "Akka", "sister"),
    ],
    "body parts": [
        ("Eye", "கண்", "Kan", "eye"),
        ("Ear", "காது", "Kaadhu", "ear"),
        ("Nose", "மூக்கு", "Mookku", "nose"),
        ("Hand", "கை", "Kai", "hand"),
    ],
    "shapes": [
        ("Circle", "வட்டம்", "Vattam", "circle"),
        ("Square", "சதுரம்", "Sathuram", "square"),
        ("Triangle", "முக்கோணம்", "Mukkonam", "triangle"),
        ("Star", "நட்சத்திரம்", "Natchathiram", "star"),
    ],
    "school": [
        ("Book", "புத்தகம்", "Puthagam", "book"),
        ("Pen", "பேனா", "Penaa", "pen"),
        ("Pencil", "பென்சில்", "Pencil", "pencil"),
        ("Bag", "பை", "Pai", "bag"),
    ],
    "vegetables": [
        ("Tomato", "தக்காளி", "Thakkaali", "tomato"),
        ("Carrot", "கேரட்", "Carrot", "carrot"),
        ("Potato", "உருளைக்கிழங்கு", "Urulaikkizhangu", "potato"),
        ("Onion", "வெங்காயம்", "Vengayam", "onion"),
    ],
}

WIDTH, HEIGHT = 854, 480
FPS = 12


# ---------- FONTS AND DRAWING HELPERS ----------

def get_font(size, bold=False):
    candidates = []
    if bold:
        candidates.extend([
            r"C:\Windows\Fonts\NirmalaB.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ])
    candidates.extend([
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ])
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def centered_text(draw, xy, text, font, fill, anchor="mm"):
    draw.text(xy, str(text), font=font, fill=fill, anchor=anchor)


def draw_oli(draw, x=120, y=250, bounce=0, wave=0, happy=True):
    """Draw Oli, the purple owl mascot, from simple shapes."""
    y = int(y + bounce)
    purple = "#9875D5"
    dark = "#5B3B87"
    cream = "#F4EAFB"
    orange = "#FFB547"

    # Tiny ear tufts
    draw.polygon([(x-54, y-68), (x-49, y-105), (x-22, y-75)], fill=purple, outline=dark)
    draw.polygon([(x+22, y-75), (x+49, y-105), (x+54, y-68)], fill=purple, outline=dark)

    # Body and wings
    draw.ellipse((x-62, y-83, x+62, y+65), fill=purple, outline=dark, width=3)
    wing_shift = int(12 * math.sin(wave)) if wave else 0
    draw.ellipse((x-77, y-15-wing_shift, x-35, y+42-wing_shift), fill="#8561C1", outline=dark, width=2)
    draw.ellipse((x+35, y-15+wing_shift, x+77, y+42+wing_shift), fill="#8561C1", outline=dark, width=2)

    # Eye patches and eyes
    draw.ellipse((x-49, y-60, x-3, y-12), fill="white")
    draw.ellipse((x+3, y-60, x+49, y-12), fill="white")
    pupil_y = y-36
    draw.ellipse((x-32, pupil_y-12, x-13, pupil_y+12), fill="#302347")
    draw.ellipse((x+13, pupil_y-12, x+32, pupil_y+12), fill="#302347")
    draw.ellipse((x-27, pupil_y-8, x-21, pupil_y-2), fill="white")
    draw.ellipse((x+18, pupil_y-8, x+24, pupil_y-2), fill="white")

    # Beak and belly
    draw.polygon([(x-13, y-12), (x+13, y-12), (x, y+7)], fill=orange, outline="#D98A20")
    draw.ellipse((x-39, y+7, x+39, y+54), fill=cream)

    # Feet
    draw.line((x-19, y+59, x-28, y+68), fill=orange, width=5)
    draw.line((x+19, y+59, x+28, y+68), fill=orange, width=5)
    centered_text(draw, (x, y+87), "OLI", get_font(20, True), dark)


def draw_sparkles(draw, phase):
    points = [(350, 105), (760, 112), (720, 390), (280, 390), (480, 85)]
    for i, (x, y) in enumerate(points):
        if (i + phase) % 2 == 0:
            r = 5 + (phase % 3)
            draw.line((x-r, y, x+r, y), fill="#F5C95C", width=3)
            draw.line((x, y-r, x, y+r), fill="#F5C95C", width=3)


def draw_star(draw, cx, cy, outer, inner, fill):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = outer if i % 2 == 0 else inner
        pts.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(pts, fill=fill, outline="#B77D24")


def draw_object(draw, kind, box, phase=0):
    """Draw simple local vector cartoons for lesson vocabulary."""
    x1, y1, x2, y2 = box
    cx, cy = (x1+x2)//2, (y1+y2)//2
    w, h = x2-x1, y2-y1
    outline = "#684B3D"

    if kind in ("apple", "banana", "mango", "orange"):
        # Fruit illustrations use distinct silhouettes, highlights, and details
        # so young learners can recognise each fruit quickly.
        if kind == "apple":
            # Apple body: two rounded lobes with a tapered bottom.
            draw.ellipse((cx-w*.29, cy-h*.23, cx+w*.29, cy+h*.19), fill="#F0444F", outline="#B92336", width=3)
            draw.ellipse((cx-w*.24, cy-h*.17, cx+w*.24, cy+h*.31), fill="#F0444F", outline="#B92336", width=3)
            draw.ellipse((cx-w*.25, cy-h*.18, cx-w*.03, cy+h*.17), fill="#F0444F")
            draw.polygon([(cx-w*.10, cy-h*.21), (cx, cy-h*.30), (cx+w*.10, cy-h*.21)], fill="#F0444F")
            draw.line((cx, cy-h*.25, cx+4, cy-h*.43), fill="#754322", width=7)
            draw.ellipse((cx+2, cy-h*.43, cx+w*.22, cy-h*.31), fill="#48A85B", outline="#2E7D46", width=2)
            draw.ellipse((cx-w*.19, cy-h*.08, cx-w*.12, cy+h*.04), fill="#FFB6AE")
            draw.ellipse((cx-w*.12, cy-h*.12, cx-w*.08, cy-h*.04), fill="#FFD5C8")
        elif kind == "banana":
            # A thick crescent-shaped banana built from curved polygon points.
            outer, inner = [], []
            for j in range(17):
                t = j / 16
                xx = cx - w*.37 + t*w*.74
                yy = cy - h*.14 + math.sin(t*math.pi)*h*.30
                outer.append((xx, yy))
            for j in range(16, -1, -1):
                t = j / 16
                xx = cx - w*.34 + t*w*.68
                yy = cy - h*.05 + math.sin(t*math.pi)*h*.12
                inner.append((xx, yy))
            draw.polygon(outer + inner, fill="#FFD84F", outline="#C69222")
            draw.line(outer, fill="#F0B92E", width=3, joint="curve")
            # Soft highlight along the banana.
            highlight = []
            for j in range(11):
                t = .12 + j*.076
                xx = cx - w*.31 + t*w*.62
                yy = cy - h*.10 + math.sin(t*math.pi)*h*.25
                highlight.append((xx, yy))
            if len(highlight) > 1:
                draw.line(highlight, fill="#FFF0A1", width=6, joint="curve")
            draw.line((cx-w*.37, cy-h*.14, cx-w*.43, cy-h*.21), fill="#6D482A", width=7)
            draw.line((cx+w*.37, cy-h*.14, cx+w*.42, cy-h*.22), fill="#6D482A", width=7)
            draw.ellipse((cx-w*.40, cy-h*.19, cx-w*.34, cy-h*.12), fill="#8C5A2B")
            draw.ellipse((cx+w*.34, cy-h*.20, cx+w*.40, cy-h*.12), fill="#8C5A2B")
        elif kind == "mango":
            # Asymmetric mango silhouette with golden and red blush.
            mango_points = [
                (cx-w*.04, cy-h*.31), (cx+w*.17, cy-h*.29),
                (cx+w*.29, cy-h*.13), (cx+w*.27, cy+h*.10),
                (cx+w*.12, cy+h*.28), (cx-w*.09, cy+h*.31),
                (cx-w*.27, cy+h*.14), (cx-w*.29, cy-h*.07),
                (cx-w*.19, cy-h*.24)
            ]
            draw.polygon(mango_points, fill="#FFB52F", outline="#D17A1A")
            draw.ellipse((cx-w*.01, cy-h*.23, cx+w*.26, cy+h*.14), fill="#F36B43")
            draw.ellipse((cx-w*.14, cy-h*.20, cx+w*.08, cy+h*.17), fill="#FFC343")
            draw.line((cx-w*.02, cy-h*.29, cx+5, cy-h*.41), fill="#754322", width=6)
            draw.ellipse((cx+2, cy-h*.43, cx+w*.20, cy-h*.34), fill="#45A85B", outline="#2E7D46", width=2)
            draw.ellipse((cx-w*.14, cy-h*.12, cx-w*.08, cy-h*.03), fill="#FFE29A")
        elif kind == "orange":
            # Round orange with peel dimples, small top indentation and leaf.
            draw.ellipse((cx-w*.29, cy-h*.27, cx+w*.29, cy+h*.29), fill="#FF982F", outline="#D66C1C", width=3)
            draw.arc((cx-w*.23, cy-h*.20, cx+w*.23, cy+h*.20), 205, 320, fill="#FFBD63", width=4)
            for dx, dy, r in [(-.15,-.12,3),(.12,-.15,3),(.19,.04,2),(-.16,.12,3),(.04,.18,2),(.02,-.02,2)]:
                px, py = cx+w*dx, cy+h*dy
                draw.ellipse((px-r, py-r, px+r, py+r), fill="#E77B21")
            draw.ellipse((cx-7, cy-h*.29, cx+7, cy-h*.24), fill="#D66C1C")
            draw.ellipse((cx+1, cy-h*.37, cx+w*.20, cy-h*.29), fill="#4BAA61", outline="#2E7D46", width=2)
    elif kind in ("cat", "dog", "cow", "elephant"):
        # A friendly animal face with different ears and snout shapes.
        face = {"cat":"#F3C58B", "dog":"#C99465", "cow":"#F7F4EE", "elephant":"#A9B5C4"}[kind]
        if kind == "cat":
            draw.polygon([(cx-w*.28, cy-h*.12), (cx-w*.25, cy-h*.39), (cx-w*.04, cy-h*.20)], fill=face, outline=outline)
            draw.polygon([(cx+w*.04, cy-h*.20), (cx+w*.25, cy-h*.39), (cx+w*.28, cy-h*.12)], fill=face, outline=outline)
        elif kind == "dog":
            draw.ellipse((cx-w*.37, cy-h*.25, cx-w*.13, cy+h*.10), fill="#9B6847", outline=outline, width=2)
            draw.ellipse((cx+w*.13, cy-h*.25, cx+w*.37, cy+h*.10), fill="#9B6847", outline=outline, width=2)
        elif kind == "cow":
            draw.ellipse((cx-w*.20, cy-h*.35, cx-w*.06, cy-h*.20), fill="#F4F4F4", outline=outline, width=2)
            draw.ellipse((cx+w*.06, cy-h*.35, cx+w*.20, cy-h*.20), fill="#F4F4F4", outline=outline, width=2)
        else:
            draw.ellipse((cx-w*.38, cy-h*.18, cx-w*.17, cy+h*.16), fill="#A9B5C4", outline=outline, width=2)
            draw.ellipse((cx+w*.17, cy-h*.18, cx+w*.38, cy+h*.16), fill="#A9B5C4", outline=outline, width=2)
        draw.ellipse((cx-w*.29, cy-h*.28, cx+w*.29, cy+h*.28), fill=face, outline=outline, width=3)
        draw.ellipse((cx-w*.15, cy-h*.06, cx-w*.08, cy+h*.01), fill="#302347")
        draw.ellipse((cx+w*.08, cy-h*.06, cx+w*.15, cy+h*.01), fill="#302347")
        if kind == "elephant":
            draw.rounded_rectangle((cx-13, cy-h*.01, cx+13, cy+h*.27), radius=10, fill=face, outline=outline, width=2)
        else:
            snout = "#F3A6A6" if kind in ("cat", "dog") else "#E7B8B8"
            draw.ellipse((cx-w*.13, cy+h*.02, cx+w*.13, cy+h*.17), fill=snout, outline=outline, width=2)
        draw.arc((cx-18, cy+4, cx+18, cy+25), 10, 170, fill=outline, width=2)
    elif kind in ("red", "blue", "green", "yellow"):
        color = {"red":"#F04444", "blue":"#438BE8", "green":"#42B96B", "yellow":"#F8D447"}[kind]
        draw.rounded_rectangle((cx-w*.28, cy-h*.28, cx+w*.28, cy+h*.28), radius=25, fill=color, outline="#FFFFFF", width=4)
        draw.ellipse((cx-w*.08, cy-h*.08, cx+w*.08, cy+h*.08), fill="#FFFFFF")
    elif kind in ("one", "two", "three", "four"):
        count = {"one":1, "two":2, "three":3, "four":4}[kind]
        for i in range(count):
            xx = cx + (i-(count-1)/2)*52
            draw.ellipse((xx-18, cy-18, xx+18, cy+18), fill=["#F05A63", "#F5BD45", "#55B9A7", "#7B86E8"][i], outline="white", width=2)
    elif kind in ("circle", "square", "triangle", "star"):
        if kind == "circle":
            draw.ellipse((cx-w*.27, cy-h*.27, cx+w*.27, cy+h*.27), fill="#65C7E8", outline="#2686A7", width=4)
        elif kind == "square":
            draw.rounded_rectangle((cx-w*.24, cy-h*.24, cx+w*.24, cy+h*.24), radius=8, fill="#FF8C69", outline="#BD573C", width=4)
        elif kind == "triangle":
            draw.polygon([(cx, cy-h*.31), (cx-w*.30, cy+h*.25), (cx+w*.30, cy+h*.25)], fill="#F7D24A", outline="#B58C1D")
        else:
            draw_star(draw, cx, cy, min(w,h)*.31, min(w,h)*.14, "#F7D24A")
    elif kind in ("book", "pen", "pencil", "bag"):
        if kind == "book":
            draw.rounded_rectangle((cx-w*.28, cy-h*.30, cx+w*.28, cy+h*.30), radius=8, fill="#E96D78", outline="#A93B49", width=3)
            draw.line((cx, cy-h*.26, cx, cy+h*.25), fill="white", width=4)
            draw.line((cx-w*.18, cy-h*.10, cx-w*.04, cy-h*.10), fill="white", width=3)
        elif kind == "pen":
            draw.rounded_rectangle((cx-12, cy-h*.30, cx+12, cy+h*.24), radius=8, fill="#438BE8", outline="#2759A1", width=2)
            draw.polygon([(cx-12, cy+h*.24), (cx+12, cy+h*.24), (cx, cy+h*.36)], fill="#D5D5D5", outline=outline)
            draw.line((cx-9, cy-h*.22, cx+9, cy-h*.22), fill="#E9F2FF", width=3)
        elif kind == "pencil":
            draw.polygon([(cx-14, cy-h*.25), (cx+14, cy-h*.25), (cx+14, cy+h*.23), (cx, cy+h*.35), (cx-14, cy+h*.23)], fill="#F6CE52", outline="#A47C1A")
            draw.polygon([(cx-14, cy-h*.25), (cx+14, cy-h*.25), (cx, cy-h*.36)], fill="#F2A7A7", outline=outline)
        else:
            draw.rounded_rectangle((cx-w*.25, cy-h*.15, cx+w*.25, cy+h*.30), radius=18, fill="#E96D78", outline="#A93B49", width=3)
            draw.arc((cx-w*.14, cy-h*.32, cx+w*.14, cy+h*.05), 180, 360, fill="#A93B49", width=5)
    elif kind in ("tomato", "carrot", "potato", "onion"):
        if kind == "tomato":
            draw.ellipse((cx-w*.27, cy-h*.20, cx+w*.27, cy+h*.25), fill="#F04D52", outline="#B92D38", width=3)
            draw.polygon([(cx, cy-h*.18), (cx-22, cy-h*.31), (cx-6, cy-h*.15), (cx+18, cy-h*.32), (cx+9, cy-h*.12)], fill="#4BAA61")
        elif kind == "carrot":
            draw.polygon([(cx-w*.20, cy-h*.24), (cx+w*.20, cy-h*.24), (cx, cy+h*.36)], fill="#F28B36", outline="#C45C1C")
            for yy in [-.10, .04, .18]:
                draw.line((cx-10, cy+h*yy, cx+10, cy+h*yy), fill="#F7C17C", width=3)
            draw.line((cx, cy-h*.23, cx-12, cy-h*.38), fill="#4BAA61", width=6)
            draw.line((cx, cy-h*.23, cx+12, cy-h*.39), fill="#4BAA61", width=6)
        elif kind == "potato":
            draw.ellipse((cx-w*.30, cy-h*.21, cx+w*.30, cy+h*.22), fill="#C99A61", outline="#8B6339", width=3)
            for dx, dy in [(-18,-5),(14,8),(4,-14)]:
                draw.ellipse((cx+dx, cy+dy, cx+dx+5, cy+dy+5), fill="#8B6339")
        else:
            draw.ellipse((cx-w*.25, cy-h*.25, cx+w*.25, cy+h*.28), fill="#D7B6D9", outline="#9A719D", width=3)
            draw.line((cx, cy-h*.24, cx+5, cy-h*.39), fill="#6A4429", width=6)
            draw.line((cx+3, cy-h*.36, cx+22, cy-h*.43), fill="#4BAA61", width=5)
    elif kind in ("eye", "ear", "nose", "hand"):
        if kind == "eye":
            draw.ellipse((cx-w*.30, cy-h*.16, cx+w*.30, cy+h*.16), fill="white", outline="#644C85", width=4)
            draw.ellipse((cx-20, cy-20, cx+20, cy+20), fill="#58A9D8", outline="#275E85", width=2)
            draw.ellipse((cx-8, cy-8, cx+8, cy+8), fill="#302347")
        elif kind == "ear":
            draw.ellipse((cx-w*.18, cy-h*.31, cx+w*.18, cy+h*.31), fill="#F2B5B5", outline="#A65E6A", width=4)
            draw.arc((cx-w*.09, cy-h*.19, cx+w*.12, cy+h*.17), 20, 290, fill="#A65E6A", width=4)
        elif kind == "nose":
            draw.polygon([(cx, cy-h*.28), (cx-w*.20, cy+h*.20), (cx+w*.20, cy+h*.20)], fill="#F2A5A5", outline="#A65E6A")
            draw.ellipse((cx-6, cy+12, cx-1, cy+17), fill="#A65E6A")
            draw.ellipse((cx+2, cy+12, cx+7, cy+17), fill="#A65E6A")
        else:
            draw.ellipse((cx-w*.17, cy-h*.24, cx+w*.17, cy+h*.06), fill="#F2B5B5", outline="#A65E6A", width=3)
            for dx in [-.16, -.05, .06, .17]:
                draw.rounded_rectangle((cx+w*dx-7, cy-h*.28, cx+w*dx+7, cy+h*.02), radius=6, fill="#F2B5B5", outline="#A65E6A", width=2)
            draw.rounded_rectangle((cx-w*.17, cy-h*.02, cx+w*.17, cy+h*.30), radius=12, fill="#F2B5B5", outline="#A65E6A", width=3)
    else:
        # General icon for greetings and family words.
        draw.ellipse((cx-w*.20, cy-h*.27, cx+w*.20, cy+h*.10), fill="#F4C6A2", outline="#8D5D46", width=3)
        draw.arc((cx-w*.18, cy-h*.12, cx+w*.18, cy+h*.16), 5, 175, fill="#8D5D46", width=3)
        draw.rounded_rectangle((cx-w*.27, cy+h*.08, cx+w*.27, cy+h*.35), radius=18, fill="#72B9E8", outline="#3C7BA3", width=3)


def make_slide(title, subtitle, lesson_word=None, number=1, phase=0):
    # Warm pastel background with simple grass and clouds.
    img = Image.new("RGB", (WIDTH, HEIGHT), "#FFF4D7")
    draw = ImageDraw.Draw(img)
    draw.ellipse((-70, 335, 360, 570), fill="#D8F0B7")
    draw.ellipse((520, 360, 930, 560), fill="#D8F0B7")
    draw.ellipse((30, 70, 150, 120), fill="#FFFFFF")
    draw.ellipse((70, 54, 180, 122), fill="#FFFFFF")
    draw.ellipse((650, 75, 750, 120), fill="#FFFFFF")
    draw.ellipse((700, 57, 790, 122), fill="#FFFFFF")

    draw.rectangle((0, 0, WIDTH, 66), fill="#DCC9FF")
    centered_text(draw, (WIDTH//2, 33), "Learn Tamil with Oli!", get_font(29, True), "#39245E")
    draw_sparkles(draw, phase)

    # Rounded main panel
    draw.rounded_rectangle((225, 98, 825, 407), radius=28, fill="#FFFFFF", outline="#DCC9FF", width=4)
    draw_oli(draw, x=120, y=245, bounce=(phase % 3) * 2, wave=phase / 2.0)

    centered_text(draw, (525, 132), title, get_font(27, True), "#39245E")

    if lesson_word:
        english, tamil, transliteration, kind = lesson_word
        draw_object(draw, kind, (270, 165, 475, 350), phase)
        centered_text(draw, (650, 190), english, get_font(29, True), "#6541A5")
        centered_text(draw, (650, 247), tamil, get_font(34, True), "#222222")
        centered_text(draw, (650, 296), transliteration, get_font(21), "#287A65")
        centered_text(draw, (650, 355), "Say it with Oli!", get_font(18, True), "#E77C4B")
    else:
        centered_text(draw, (525, 218), subtitle, get_font(23), "#333333")
        # Decorative stars on title cards
        draw_star(draw, 390, 300, 22, 10, "#FFD45C")
        draw_star(draw, 660, 300, 22, 10, "#FFD45C")

    centered_text(draw, (WIDTH//2, 448), f"Let's learn together!  •  Scene {number}", get_font(17), "#6541A5")
    return img


# ---------- AUDIO HELPERS ----------

async def save_speech(text, voice, output_path, rate):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=f"{rate:+d}%")
    await communicate.save(str(output_path))


def wav_duration(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def combine_wav_files(paths, output_path):
    if not paths:
        raise RuntimeError("No narration clips were generated.")
    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
        chunks = [first.readframes(first.getnframes())]
    for path in paths[1:]:
        with wave.open(str(path), "rb") as clip:
            if clip.getparams()[:3] != params[:3]:
                raise RuntimeError("Narration clips have different audio formats.")
            chunks.append(clip.readframes(clip.getnframes()))
    with wave.open(str(output_path), "wb") as output:
        output.setparams(params)
        for chunk in chunks:
            output.writeframes(chunk)


def convert_mp3_to_wav(ffmpeg, mp3_path, wav_path):
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(mp3_path), "-ar", "24000", "-ac", "1",
         "-c:a", "pcm_s16le", str(wav_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Could not convert narration audio:\n" + result.stderr[-1500:])


# ---------- VIDEO GENERATION ----------

def create_video(topic, words, tamil_voice, speed):
    with tempfile.TemporaryDirectory() as temp_folder:
        temp = Path(temp_folder)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        english_voice = "en-IN-NeerjaNeural"

        scenes = [
            ("Meet Oli!", "Let's learn some Tamil words together!", None, [
                (english_voice, "Hello, little learners! I am Oli. "
                 f"Today we are learning {topic}. Are you ready? Let's begin!")
            ])
        ]

        for word in words:
            english, tamil, transliteration, kind = word
            scenes.append(("Let's learn!", "", word, [
                (english_voice, f"This is {english}. In Tamil, listen carefully."),
                (tamil_voice, tamil),
                (english_voice, f"Can you say {tamil}? Great job!")
            ]))

        scenes.append(("Let's remember!", "Can you say the words with Oli?", None, [
            (english_voice, "Wonderful! Let's practise those Tamil words again."),
            (tamil_voice, " ... ".join(word[1] for word in words)),
        ]))
        scenes.append(("Goodbye, friends!", "See you in the next lesson!", None, [
            (english_voice, "You did a wonderful job learning Tamil today. Keep practising. Goodbye, friends!")
        ]))

        audio_paths = []
        for i, scene in enumerate(scenes):
            segment_paths = []
            for j, (voice, speech_text) in enumerate(scene[3]):
                mp3_path = temp / f"scene_{i}_{j}.mp3"
                wav_path = temp / f"scene_{i}_{j}.wav"
                asyncio.run(save_speech(speech_text, voice, mp3_path, speed))
                convert_mp3_to_wav(ffmpeg, mp3_path, wav_path)
                segment_paths.append(wav_path)
            scene_audio = temp / f"scene_{i}.wav"
            combine_wav_files(segment_paths, scene_audio)
            audio_paths.append(scene_audio)

        narration_path = temp / "narration.wav"
        combine_wav_files(audio_paths, narration_path)

        # Calculate scene durations from the actual audio; rounding up to whole frames prevents clipping.
        durations = [wav_duration(path) for path in audio_paths]
        silent_path = temp / "silent.mp4"

        with imageio.get_writer(
            str(silent_path), fps=FPS, codec="libx264", macro_block_size=16
        ) as writer:
            for i, scene in enumerate(scenes):
                frames = max(FPS, math.ceil(durations[i] * FPS))
                for frame_index in range(frames):
                    phase = frame_index // 3
                    slide = make_slide(scene[0], scene[1], scene[2], i + 1, phase)
                    writer.append_data(imageio.core.asarray(slide))

        safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic).strip("_") or "Tamil_Lesson"
        output_path = VIDEO_DIR / f"{safe_topic}_lesson.mp4"

        # Do not use -shortest: preserve the full narration and video.
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(silent_path), "-i", str(narration_path),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-map", "0:v:0", "-map", "1:a:0", "-movflags", "+faststart",
             str(output_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError("Could not combine the video and audio:\n" + result.stderr[-2000:])
        return output_path


# ---------- WEBSITE ----------

topic = st.text_input("What should Oli teach?", "Fruits")
topic_key = topic.strip().lower()

matching_key = next(
    (key for key in LESSONS if key in topic_key or topic_key in key),
    None
)

if matching_key:
    st.success(f"Lesson found: {matching_key.title()}")
    st.write("Words in this lesson:")
    st.write(", ".join(word[0] for word in LESSONS[matching_key]))
else:
    st.info("Try: fruits, animals, colors, numbers, greetings, family, body parts, shapes, school, or vegetables.")

tamil_voices = {
    "Pallavi — Female Tamil": "ta-IN-PallaviNeural",
    "Valluvar — Male Tamil": "ta-IN-ValluvarNeural",
}
selected_voice_label = st.selectbox("Tamil pronunciation voice", list(tamil_voices.keys()))
selected_voice = tamil_voices[selected_voice_label]

speed = st.slider("Speaking speed adjustment (%)", min_value=-20, max_value=20, value=-5)

st.caption("Illustrations are drawn by Python on your computer. Tamil narration uses the online edge-tts service.")

if st.button("🎬 Generate My Tamil Video", type="primary"):
    if not matching_key:
        st.error("Please enter a supported lesson topic.")
    else:
        try:
            with st.spinner("Oli is drawing the cartoons and creating narration. This may take a few minutes..."):
                video_path = create_video(matching_key.title(), LESSONS[matching_key], selected_voice, speed)
            st.success("Your video is ready!")
            st.video(str(video_path))
            with open(video_path, "rb") as video_file:
                st.download_button(
                    "⬇️ Download MP4 Video",
                    data=video_file.read(),
                    file_name=video_path.name,
                    mime="video/mp4",
                )
            st.caption(f"Saved on your computer: {video_path}")
        except Exception as error:
            st.error("The video could not be created.")
            st.code(str(error))
