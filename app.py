
import os
import re
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

st.set_page_config(page_title="Oli AI Studio", page_icon="🦉")

st.title("🦉 Oli AI Studio")
st.write("Create Tamil learning videos for children with Oli!")

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "OliVideos"
VIDEO_DIR.mkdir(exist_ok=True)

LESSONS = {
    "fruits": [
        ("Apple", "ஆப்பிள்", "Aappil"),
        ("Banana", "வாழைப்பழம்", "Vaazhaipazham"),
        ("Mango", "மாம்பழம்", "Maampazham"),
        ("Orange", "ஆரஞ்சு", "Aaranju"),
    ],
    "animals": [
        ("Cat", "பூனை", "Poonai"),
        ("Dog", "நாய்", "Naai"),
        ("Cow", "பசு", "Pasu"),
        ("Elephant", "யானை", "Yaanai"),
    ],
    "colors": [
        ("Red", "சிவப்பு", "Sivappu"),
        ("Blue", "நீலம்", "Neelam"),
        ("Green", "பச்சை", "Pachai"),
        ("Yellow", "மஞ்சள்", "Manjal"),
    ],
    "numbers": [
        ("One", "ஒன்று", "Ondru"),
        ("Two", "இரண்டு", "Irandu"),
        ("Three", "மூன்று", "Moondru"),
        ("Four", "நான்கு", "Naangu"),
    ],
    "greetings": [
        ("Hello", "வணக்கம்", "Vanakkam"),
        ("Thank you", "நன்றி", "Nandri"),
        ("Come", "வா", "Vaa"),
        ("Go", "போ", "Poo"),
    ],
    "family": [
        ("Mother", "அம்மா", "Amma"),
        ("Father", "அப்பா", "Appa"),
        ("Older brother", "அண்ணா", "Anna"),
        ("Older sister", "அக்கா", "Akka"),
    ],
    "body parts": [
        ("Eye", "கண்", "Kan"),
        ("Ear", "காது", "Kaadhu"),
        ("Nose", "மூக்கு", "Mookku"),
        ("Hand", "கை", "Kai"),
    ],
    "shapes": [
        ("Circle", "வட்டம்", "Vattam"),
        ("Square", "சதுரம்", "Sathuram"),
        ("Triangle", "முக்கோணம்", "Mukkonam"),
        ("Star", "நட்சத்திரம்", "Natchathiram"),
    ],
    "school": [
        ("Book", "புத்தகம்", "Puthagam"),
        ("Pen", "பேனா", "Penaa"),
        ("Pencil", "பென்சில்", "Pencil"),
        ("Bag", "பை", "Pai"),
    ],
    "vegetables": [
        ("Tomato", "தக்காளி", "Thakkaali"),
        ("Carrot", "கேரட்", "Carrot"),
        ("Potato", "உருளைக்கிழங்கு", "Urulaikkizhangu"),
        ("Onion", "வெங்காயம்", "Vengayam"),
    ],
}


# ---------- DRAWING ----------

WIDTH = 854
HEIGHT = 480


def get_font(size):
    candidates = [
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\NirmalaB.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]

    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                pass

    return ImageFont.load_default()


def draw_oli(draw, x=125, y=210):
    # Draw Oli using simple shapes.
    draw.ellipse(
        (x - 62, y - 72, x + 62, y + 65),
        fill="#9B78D0",
        outline="#61448B",
        width=3,
    )

    # Eyes
    draw.ellipse(
        (x - 48, y - 48, x - 5, y - 5),
        fill="white",
    )
    draw.ellipse(
        (x + 5, y - 48, x + 48, y - 5),
        fill="white",
    )

    draw.ellipse(
        (x - 32, y - 36, x - 17, y - 20),
        fill="#302347",
    )
    draw.ellipse(
        (x + 17, y - 36, x + 32, y - 20),
        fill="#302347",
    )

    # Beak and belly
    draw.polygon(
        [(x - 12, y - 8), (x + 12, y - 8), (x, y + 8)],
        fill="#FFB84D",
    )
    draw.ellipse(
        (x - 39, y + 12, x + 39, y + 55),
        fill="#EADCFB",
    )

    draw.text(
        (x - 25, y + 68),
        "OLI",
        font=get_font(22),
        fill="#61448B",
    )


def make_slide(title, subtitle, lesson_word=None, number=1):
    img = Image.new("RGB", (WIDTH, HEIGHT), "#FFF5D9")
    draw = ImageDraw.Draw(img)

    draw.rectangle(
        (0, 0, WIDTH, 70),
        fill="#DCC9FF",
    )

    draw.text(
        (28, 17),
        "Learn Tamil with Oli!",
        font=get_font(30),
        fill="#39245E",
    )

    draw_oli(draw)

    draw.rounded_rectangle(
        (235, 105, 820, 390),
        radius=28,
        fill="white",
        outline="#DCC9FF",
        width=4,
    )

    draw.text(
        (265, 130),
        title,
        font=get_font(29),
        fill="#39245E",
    )

    if lesson_word:
        english, tamil, transliteration = lesson_word

        draw.text(
            (270, 195),
            english,
            font=get_font(30),
            fill="#6541A5",
        )

        draw.text(
            (270, 245),
            tamil,
            font=get_font(38),
            fill="#222222",
        )

        draw.text(
            (270, 310),
            transliteration,
            font=get_font(25),
            fill="#287A65",
        )
    else:
        draw.text(
            (265, 205),
            subtitle,
            font=get_font(24),
            fill="#333333",
        )

    draw.text(
        (28, 435),
        f"Lesson scene {number}",
        font=get_font(18),
        fill="#6541A5",
    )

    return img


# ---------- AUDIO HELPERS ----------

async def save_speech(text, voice, output_path, rate):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=f"{rate:+d}%",
    )

    await communicate.save(str(output_path))


def wav_duration(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def combine_wav_files(paths, output_path):
    if not paths:
        raise RuntimeError("No narration clips were generated.")

    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
        frames = [first.readframes(first.getnframes())]

    for path in paths[1:]:
        with wave.open(str(path), "rb") as clip:
            if clip.getparams()[:3] != params[:3]:
                raise RuntimeError(
                    "Narration clips have different audio formats."
                )

            frames.append(clip.readframes(clip.getnframes()))

    with wave.open(str(output_path), "wb") as output:
        output.setparams(params)

        for chunk in frames:
            output.writeframes(chunk)


def convert_mp3_to_wav(ffmpeg, mp3_path, wav_path):
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", str(mp3_path),
            "-ar", "24000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(wav_path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Could not convert narration audio:\n"
            + result.stderr[-1500:]
        )


# ---------- VIDEO GENERATION ----------

def create_video(topic, words, tamil_voice, speed):
    with tempfile.TemporaryDirectory() as temp_folder:
        temp = Path(temp_folder)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        # Indian English voice for explanations.
        english_voice = "en-IN-NeerjaNeural"

        scenes = [
            (
                "Meet Oli!",
                "Let's learn some Tamil words together!",
                None,
                [
                    (
                        english_voice,
                        "Hello, little learners! I am Oli. "
                        f"Today we are learning {topic}. "
                        "Are you ready? Let's begin!",
                    )
                ],
            )
        ]

        # Each vocabulary item gets an English explanation
        # followed by the actual Tamil text spoken by a Tamil voice.
        for word in words:
            english, tamil, transliteration = word

            scenes.append(
                (
                    "Let's learn!",
                    "",
                    word,
                    [
                        (
                            english_voice,
                            f"In Tamil, we say {english}. "
                            "Listen carefully.",
                        ),
                        (tamil_voice, tamil),
                    ],
                )
            )

        scenes.append(
            (
                "Let's remember!",
                "Can you say the words with Oli?",
                None,
                [
                    (
                        english_voice,
                        "Wonderful! Let's practise those Tamil words again.",
                    ),
                    (
                        tamil_voice,
                        " ... ".join(word[1] for word in words),
                    ),
                ],
            )
        )

        scenes.append(
            (
                "Goodbye, friends!",
                "See you in the next lesson!",
                None,
                [
                    (
                        english_voice,
                        "You did a wonderful job learning Tamil today. "
                        "Keep practising. Goodbye, friends!",
                    )
                ],
            )
        )

        audio_paths = []

        # Generate audio for each scene.
        for i, scene in enumerate(scenes):
            segment_paths = []

            for j, (voice, text) in enumerate(scene[3]):
                mp3_path = temp / f"scene_{i}_{j}.mp3"
                wav_path = temp / f"scene_{i}_{j}.wav"

                asyncio.run(
                    save_speech(
                        text,
                        voice,
                        mp3_path,
                        speed,
                    )
                )

                convert_mp3_to_wav(
                    ffmpeg,
                    mp3_path,
                    wav_path,
                )

                segment_paths.append(wav_path)

            scene_audio = temp / f"scene_{i}.wav"

            combine_wav_files(
                segment_paths,
                scene_audio,
            )

            audio_paths.append(scene_audio)

        # Render the illustrated slides.
        silent_path = temp / "silent.mp4"
        fps = 12

        with imageio.get_writer(
            str(silent_path),
            fps=fps,
            codec="libx264",
            macro_block_size=16,
        ) as writer:
            for i, scene in enumerate(scenes):
                slide = make_slide(
                    scene[0],
                    scene[1],
                    scene[2],
                    i + 1,
                )

                frame = imageio.core.asarray(slide)
                duration = wav_duration(audio_paths[i])

                frame_count = max(12, int(duration * fps))

                for _ in range(frame_count):
                    writer.append_data(frame)

        # Combine all scene narration.
        narration_path = temp / "narration.wav"

        combine_wav_files(
            audio_paths,
            narration_path,
        )

        safe_topic = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            topic,
        ).strip("_") or "Tamil_Lesson"

        output_path = VIDEO_DIR / f"{safe_topic}_lesson.mp4"

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i", str(silent_path),
                "-i", str(narration_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Could not combine the video and audio:\n"
                + result.stderr[-2000:]
            )

        return output_path


# ---------- WEBSITE ----------

topic = st.text_input(
    "What should Oli teach?",
    "Fruits",
)

topic_key = topic.strip().lower()

matching_key = next(
    (
        key for key in LESSONS
        if key in topic_key or topic_key in key
    ),
    None,
)

if matching_key:
    st.success(f"Lesson found: {matching_key.title()}")

    st.write("Words in this lesson:")

    st.write(
        ", ".join(word[0] for word in LESSONS[matching_key])
    )
else:
    st.info(
        "Try: fruits, animals, colors, numbers, greetings, "
        "family, body parts, shapes, school, or vegetables."
    )

tamil_voices = {
    "Pallavi — Female Tamil": "ta-IN-PallaviNeural",
    "Valluvar — Male Tamil": "ta-IN-ValluvarNeural",
}

selected_voice_label = st.selectbox(
    "Tamil pronunciation voice",
    list(tamil_voices.keys()),
)

selected_voice = tamil_voices[selected_voice_label]

speed = st.slider(
    "Speaking speed adjustment (%)",
    min_value=-20,
    max_value=20,
    value=0,
)

if st.button("🎬 Generate My Tamil Video", type="primary"):
    if not matching_key:
        st.error(
            "Please enter a supported lesson topic."
        )
    else:
        try:
            with st.spinner(
                "Oli is creating the illustrations and narration..."
            ):
                video_path = create_video(
                    matching_key.title(),
                    LESSONS[matching_key],
                    selected_voice,
                    speed,
                )

            st.success("Your video is ready!")

            st.video(str(video_path))

            with open(video_path, "rb") as video_file:
                st.download_button(
                    "⬇️ Download MP4 Video",
                    data=video_file.read(),
                    file_name=video_path.name,
                    mime="video/mp4",
                )

            st.caption(
                f"Saved on your computer: {video_path}"
            )

        except Exception as error:
            st.error("The video could not be created.")

            st.code(str(error))
