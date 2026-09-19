import os
import re
import time
import random
import requests
import streamlit as st
from google import genai
from google.genai.errors import ServerError, APIError
from gtts import gTTS
from pydub import AudioSegment
from proglog import ProgressBarLogger

# ElevenLabs (opsional - hanya dipakai jika mode ElevenLabs dipilih)
try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA MODERN
# ==========================================
st.set_page_config(page_title="AI Video Studio Pro v10 (3 Voice Modes)", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    h1 { color: #38BDF8 !important; font-weight: 800; text-align: center; margin-bottom: 8px; }
    h2, h3, h4, h5, h6, .stCaption { color: #E2E8F0 !important; }
    label, .stWidgetLabel p { color: #F1F5F9 !important; font-weight: 600 !important; font-size: 15px !important; }
    .stTextInput input, .stTextArea textarea {
        background-color: #1E293B !important; color: #FFFFFF !important;
        border-radius: 8px !important; border: 1px solid #475569 !important; font-size: 15px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #1E293B !important; color: #FFFFFF !important;
        border-radius: 8px !important; border: 1px solid #475569 !important;
    }
    div[data-baseweb="select"] span { color: #FFFFFF !important; }
    section[data-testid="stFileUploadDropzone"] {
        background-color: #1E293B !important; border: 2px dashed #38BDF8 !important; border-radius: 10px !important;
    }
    .stButton>button {
        width: 100%; background: linear-gradient(135deg, #0284C7, #38BDF8);
        color: #FFFFFF !important; border: none; padding: 14px 24px;
        font-size: 18px; font-weight: bold; border-radius: 10px; transition: all 0.3s ease;
        box-shadow: 0px 4px 12px rgba(56, 189, 248, 0.3);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0px 6px 20px rgba(56, 189, 248, 0.5); }
    .music-badge {
        display: inline-block; background: linear-gradient(135deg, #7C3AED, #A855F7);
        color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px;
        font-weight: bold; margin-bottom: 8px;
    }
    .vo-badge {
        display: inline-block; background: linear-gradient(135deg, #059669, #10B981);
        color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px;
        font-weight: bold; margin-bottom: 8px;
    }
    .video-badge {
        display: inline-block; background: linear-gradient(135deg, #DC2626, #F97316);
        color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px;
        font-weight: bold; margin-bottom: 8px;
    }
    .upload-badge {
        display: inline-block; background: linear-gradient(135deg, #0891B2, #06B6D4);
        color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px;
        font-weight: bold; margin-bottom: 8px;
    }
    .google-badge {
        display: inline-block; background: linear-gradient(135deg, #DB4437, #EA4335);
        color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px;
        font-weight: bold; margin-bottom: 8px;
    }
    .eleven-badge {
        display: inline-block; background: linear-gradient(135deg, #4338CA, #6366F1);
        color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px;
        font-weight: bold; margin-bottom: 8px;
    }
    .info-box {
        background-color: #1E293B; border-left: 4px solid #10B981;
        padding: 12px 16px; border-radius: 6px; margin: 8px 0; color: #F1F5F9;
    }
    .info-box-video {
        background-color: #1E293B; border-left: 4px solid #F97316;
        padding: 12px 16px; border-radius: 6px; margin: 8px 0; color: #F1F5F9;
    }
    .info-box-music {
        background-color: #1E293B; border-left: 4px solid #06B6D4;
        padding: 12px 16px; border-radius: 6px; margin: 8px 0; color: #F1F5F9;
    }
    .info-box-voice {
        background-color: #1E293B; border-left: 4px solid #6366F1;
        padding: 12px 16px; border-radius: 6px; margin: 8px 0; color: #F1F5F9;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER API KEYS & VOICE CONFIG
# ==========================================
# Ambil API Key dari secrets (aman untuk lokal & cloud)
try:
    DEFAULT_GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    DEFAULT_GEMINI_KEY = ""

try:
    DEFAULT_PEXELS_KEY = st.secrets["PEXELS_API_KEY"]
except Exception:
    DEFAULT_PEXELS_KEY = ""

try:
    DEFAULT_ELEVEN_KEY = st.secrets["ELEVENLABS_API_KEY"]
except Exception:
    DEFAULT_ELEVEN_KEY = ""

# ElevenLabs Voice Database (dari app_v5.py)
ELEVENLABS_VOICE_DATABASE = {
    "Pria": {
        "Berita News": "JBFqnCBsd6RMkjVDRZzb",
        "Edukasi": "pNInz6obpgDQGcFmaJgB",
        "Presentasi": "pNInz6obpgDQGcFmaJgB",
        "Dongeng": "JBFqnCBsd6RMkjVDRZzb",
        "Sejarah": "pNInz6obpgDQGcFmaJgB"
    },
    "Wanita": {
        "Berita News": "21m00Tcm4TlvDq8ikWAM",
        "Edukasi": "21m00Tcm4TlvDq8ikWAM",
        "Presentasi": "AZnzlk1XvdvUeBnXmlld",
        "Dongeng": "piTKgcLEGmPE4e6mEKli",
        "Sejarah": "21m00Tcm4TlvDq8ikWAM"
    }
}

# ==========================================
# 2b. FREE MUSIC LIBRARY (ROYALTY-FREE / CC0)
# ==========================================
FREE_MUSIC_LIBRARY = {
    "Pendidikan": [
        {"name": "Inspirational Corporate", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=inspirational-corporate-112196.mp3", "mood": "inspiratif, membangun"},
        {"name": "Soft Piano Documentary", "url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=documentary-112917.mp3", "mood": "tenang, fokus"},
        {"name": "Study & Learning", "url": "https://cdn.pixabay.com/download/audio/2021/11/25/audio_00fa5593f3.mp3?filename=study-and-learning-11454.mp3", "mood": "belajar, kalem"}
    ],
    "Sejarah": [
        {"name": "Cinematic Documentary", "url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3?filename=cinematic-documentary-112234.mp3", "mood": "epik, dramatis"},
        {"name": "Ancient Mystery", "url": "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946bcb78a5.mp3?filename=ancient-mystery-124883.mp3", "mood": "misterius, kuno"},
        {"name": "Epic Historical", "url": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_88447e769f.mp3?filename=epic-112238.mp3", "mood": "heroik, megah"}
    ],
    "Tutorial": [
        {"name": "Upbeat Technology", "url": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_1c1f3b5e0e.mp3?filename=technology-112234.mp3", "mood": "modern, teknologi"},
        {"name": "Happy Tutorial", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=happy-tutorial-112196.mp3", "mood": "ceria, mudah"},
        {"name": "Clean Corporate", "url": "https://cdn.pixabay.com/download/audio/2021/09/06/audio_c8c8a73467.mp3?filename=clean-corporate-112917.mp3", "mood": "rapi, profesional"}
    ],
    "Pengetahuan": [
        {"name": "Ambient Discovery", "url": "https://cdn.pixabay.com/download/audio/2022/08/02/audio_2d7c40e5a4.mp3?filename=ambient-discovery-124883.mp3", "mood": "eksploratif, luas"},
        {"name": "Curious Mind", "url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3?filename=curious-mind-112234.mp3", "mood": "penasaran, ringan"},
        {"name": "Nature Documentary", "url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=nature-documentary-112917.mp3", "mood": "alami, tenang"}
    ],
    "Bisnis": [
        {"name": "Corporate Success", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=corporate-success-112196.mp3", "mood": "sukses, optimis"},
        {"name": "Motivational Business", "url": "https://cdn.pixabay.com/download/audio/2021/11/25/audio_00fa5593f3.mp3?filename=motivational-business-11454.mp3", "mood": "motivasi, semangat"},
        {"name": "Modern Corporate", "url": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_1c1f3b5e0e.mp3?filename=modern-corporate-112234.mp3", "mood": "bersih, modern"}
    ],
    "Hiburan": [
        {"name": "Fun Upbeat", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=fun-upbeat-112196.mp3", "mood": "seru, ceria"},
        {"name": "Playful Energy", "url": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_1c1f3b5e0e.mp3?filename=playful-energy-112234.mp3", "mood": "lucu, ringan"},
        {"name": "Happy Vibes", "url": "https://cdn.pixabay.com/download/audio/2021/11/25/audio_00fa5593f3.mp3?filename=happy-vibes-11454.mp3", "mood": "positif, gembira"}
    ],
    "Default": [
        {"name": "Calm Background", "url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=calm-background-112917.mp3", "mood": "tenang, netral"},
        {"name": "Soft Ambient", "url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3?filename=soft-ambient-112234.mp3", "mood": "lembut, mengalir"},
        {"name": "Gentle Piano", "url": "https://cdn.pixabay.com/download/audio/2022/08/02/audio_2d7c40e5a4.mp3?filename=gentle-piano-124883.mp3", "mood": "piano, reflektif"}
    ]
}

# ==========================================
# 2c. FUNGSI BACKGROUND MUSIC ENGINE
# ==========================================
def get_music_for_topic(kategori, gaya_narator, deskripsi=""):
    gaya_to_kategori = {
        "Sejarah": "Sejarah",
        "Edukasi": "Pendidikan",
        "Berita News": "Pengetahuan",
        "Presentasi": "Bisnis",
        "Dongeng": "Hiburan",
    }

    if kategori in FREE_MUSIC_LIBRARY:
        pool = FREE_MUSIC_LIBRARY[kategori]
    elif gaya_narator in gaya_to_kategori:
        pool = FREE_MUSIC_LIBRARY.get(gaya_to_kategori[gaya_narator], FREE_MUSIC_LIBRARY["Default"])
    else:
        pool = FREE_MUSIC_LIBRARY["Default"]

    return random.choice(pool)


def download_background_music(music_info, output_path="temp_background_music.mp3"):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(music_info["url"], headers=headers, timeout=30, stream=True)
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            if os.path.getsize(output_path) > 1024:
                return output_path
    except Exception:
        pass
    return None


def mix_narration_with_music(narration_path, music_path, output_path,
                              music_volume_db=-18.0, fade_in_ms=2000,
                              fade_out_ms=3000, ducking=True):
    narration = AudioSegment.from_file(narration_path)
    music = AudioSegment.from_file(music_path)

    music = music.set_frame_rate(narration.frame_rate)
    music = music.set_channels(narration.channels)

    if len(music) < len(narration):
        loop_count = (len(narration) // len(music)) + 1
        music = music * loop_count

    music = music[:len(narration)]
    music = music + music_volume_db

    if fade_in_ms > 0:
        music = music.fade_in(min(fade_in_ms, len(music) // 4))
    if fade_out_ms > 0:
        music = music.fade_out(min(fade_out_ms, len(music) // 4))

    if ducking:
        try:
            chunk_ms = 500
            ducked_segments = []
            for i in range(0, len(music), chunk_ms):
                music_chunk = music[i:i + chunk_ms]
                narration_chunk = narration[i:i + chunk_ms]
                narr_db = narration_chunk.dBFS if len(narration_chunk) > 0 else -100
                if narr_db > -35:
                    music_chunk = music_chunk - 6
                ducked_segments.append(music_chunk)
            music = sum(ducked_segments)
        except Exception:
            pass

    combined = narration.overlay(music)

    if combined.max_dBFS > -0.5:
        combined = combined - (combined.max_dBFS + 0.5)

    combined.export(output_path, format="mp3", bitrate="192k")
    return output_path


def auto_background_music_pipeline(narration_audio_path, kategori, gaya_narator,
                                    deskripsi="", output_path="temp_mixed_audio.mp3",
                                    music_volume_db=-18.0):
    music_info = get_music_for_topic(kategori, gaya_narator, deskripsi)
    music_path = download_background_music(music_info)

    if not music_path:
        return narration_audio_path, None

    try:
        mixed = mix_narration_with_music(
            narration_path=narration_audio_path,
            music_path=music_path,
            output_path=output_path,
            music_volume_db=music_volume_db,
            fade_in_ms=2000,
            fade_out_ms=3000,
            ducking=True
        )
        return mixed, music_info
    except Exception:
        return narration_audio_path, None


# ==========================================
# 2c-2. FUNGSI BACKGROUND MUSIC MANUAL UPLOAD
# ==========================================
def save_uploaded_music(uploaded_file, output_path="temp_uploaded_music.mp3"):
    try:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        raw_path = f"temp_music_raw{ext}"
        with open(raw_path, "wb") as f:
            f.write(uploaded_file.read())

        if ext != ".mp3":
            audio = AudioSegment.from_file(raw_path)
            audio.export(output_path, format="mp3", bitrate="192k")
            try:
                os.remove(raw_path)
            except Exception:
                pass
        else:
            os.replace(raw_path, output_path)

        return output_path
    except Exception as e:
        raise Exception(f"Gagal memproses file musik: {str(e)}")


def manual_background_music_pipeline(narration_audio_path, uploaded_music_file,
                                      output_path="temp_mixed_audio_manual.mp3",
                                      music_volume_db=-18.0,
                                      ducking=True):
    try:
        music_path = save_uploaded_music(uploaded_music_file, "temp_manual_music.mp3")
        music_duration = get_audio_duration(music_path)

        music_info = {
            "name": f"Custom Upload: {uploaded_music_file.name}",
            "mood": "Manual Upload",
            "duration": music_duration
        }

        mixed = mix_narration_with_music(
            narration_path=narration_audio_path,
            music_path=music_path,
            output_path=output_path,
            music_volume_db=music_volume_db,
            fade_in_ms=2000,
            fade_out_ms=3000,
            ducking=ducking
        )
        return mixed, music_info
    except Exception:
        return narration_audio_path, None


# ==========================================
# 2d. UTILITAS AUDIO UPLOAD
# ==========================================
def save_uploaded_voice_over(uploaded_file, output_path="temp_uploaded_vo.mp3"):
    try:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        raw_path = f"temp_vo_raw{ext}"
        with open(raw_path, "wb") as f:
            f.write(uploaded_file.read())

        if ext != ".mp3":
            audio = AudioSegment.from_file(raw_path)
            audio.export(output_path, format="mp3", bitrate="192k")
            try:
                os.remove(raw_path)
            except Exception:
                pass
        else:
            os.replace(raw_path, output_path)

        return output_path
    except Exception as e:
        raise Exception(f"Gagal memproses file voice over: {str(e)}")


def get_audio_duration(audio_path):
    try:
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception:
        return 0.0


# ==========================================
# 2e. ELEVENLABS - VOICE OVER (BARU v10)
# ==========================================
def get_elevenlabs_user_info(api_key):
    """Cek sisa kuota ElevenLabs (dari app_v5.py)."""
    if not api_key or not api_key.strip():
        return "⚠️ Masukkan ElevenLabs API Key yang valid."

    if not ELEVENLABS_AVAILABLE:
        return "⚠️ Library ElevenLabs belum terinstall. Jalankan: pip install elevenlabs"

    try:
        client = ElevenLabs(api_key=api_key.strip())
        user_info = client.user.get()
        subscription = user_info.subscription
        used = subscription.character_count
        limit = subscription.character_limit
        remaining = limit - used
        return f"📊 **Sisa Kuota ElevenLabs:** {remaining:,} / {limit:,} karakter"
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "unauthorized" in err_msg.lower() or "missing_permissions" in err_msg.lower():
            return "💡 **Status API Key:** Terhubung (Fitur cek sisa kuota membutuhkan izin `user_read` di Dashboard ElevenLabs)."
        return f"⚠️ Status Kuota: Tidak dapat diverifikasi ({err_msg})"


def create_audio_elevenlabs(eleven_key, text, output_path, gender_key, gaya_narator):
    """Generate audio via ElevenLabs (dari app_v5.py)."""
    if not ELEVENLABS_AVAILABLE:
        raise Exception("Library ElevenLabs belum terinstall. Jalankan: pip install elevenlabs")

    client = ElevenLabs(api_key=eleven_key.strip())
    voice_id_target = ELEVENLABS_VOICE_DATABASE.get(gender_key, {}).get(gaya_narator)

    if not voice_id_target:
        voice_id_target = "21m00Tcm4TlvDq8ikWAM" if gender_key == "Wanita" else "pNInz6obpgDQGcFmaJgB"

    try:
        audio = client.text_to_speech.convert(
            voice_id=voice_id_target,
            text=text,
            model_id="eleven_multilingual_v2"
        )
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
    except Exception:
        fallback_id = "21m00Tcm4TlvDq8ikWAM" if gender_key == "Wanita" else "pNInz6obpgDQGcFmaJgB"
        audio = client.text_to_speech.convert(
            voice_id=fallback_id,
            text=text,
            model_id="eleven_multilingual_v2"
        )
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)


# ==========================================
# 2f. AUTO DOWNLOAD STOCK VIDEO (PEXELS VIDEOS)
# ==========================================
def auto_download_stock_videos(query, count=3, pexels_key=None, orientation="portrait"):
    downloaded_paths = []
    active_key = pexels_key.strip() if (pexels_key and pexels_key.strip()) else DEFAULT_PEXELS_KEY

    if not active_key:
        return downloaded_paths

    orientation_map = {"portrait": "portrait", "landscape": "landscape"}
    orientation_param = orientation_map.get(orientation, "portrait")

    try:
        headers = {"Authorization": active_key}
        url = (
            f"https://api.pexels.com/videos/search?"
            f"query={query}&per_page={count}&orientation={orientation_param}&size=medium"
        )
        res = requests.get(url, headers=headers, timeout=15)

        if res.status_code != 200:
            return downloaded_paths

        data = res.json()
        for i, video in enumerate(data.get("videos", [])):
            video_files = video.get("video_files", [])
            if not video_files:
                continue

            chosen_file = None
            for vf in sorted(video_files, key=lambda x: x.get("width", 0)):
                width = vf.get("width", 0)
                if 720 <= width <= 1920:
                    chosen_file = vf
                    break

            if not chosen_file:
                chosen_file = video_files[0]

            video_url = chosen_file.get("link")
            if not video_url:
                continue

            try:
                vid_data = requests.get(video_url, timeout=30, stream=True)
                if vid_data.status_code == 200:
                    filename = f"auto_video_{i}.mp4"
                    with open(filename, "wb") as f:
                        for chunk in vid_data.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(filename) > 100 * 1024:
                        downloaded_paths.append(filename)
                    else:
                        try:
                            os.remove(filename)
                        except Exception:
                            pass
            except Exception:
                continue

    except Exception:
        pass

    return downloaded_paths


def auto_download_visuals_mixed(query, total_count=5, photo_ratio=0.5,
                                 pexels_key=None, orientation="portrait",
                                 enable_video=True):
    stats = {"photos": 0, "videos": 0, "failed": 0}
    visual_paths = []

    if not enable_video:
        photos = auto_download_visuals_photos(query, total_count, pexels_key, orientation)
        stats["photos"] = len(photos)
        return photos, stats

    video_count = int(total_count * (1 - photo_ratio))
    photo_count = total_count - video_count

    if video_count > 0:
        videos = auto_download_stock_videos(query, video_count, pexels_key, orientation)
        visual_paths.extend(videos)
        stats["videos"] = len(videos)

        if len(videos) < video_count:
            stats["failed"] += (video_count - len(videos))
            photo_count += (video_count - len(videos))

    if photo_count > 0:
        photos = auto_download_visuals_photos(query, photo_count, pexels_key, orientation)
        visual_paths.extend(photos)
        stats["photos"] = len(photos)

        if len(photos) < photo_count:
            stats["failed"] += (photo_count - len(photos))

    random.shuffle(visual_paths)

    return visual_paths, stats


def auto_download_visuals_photos(query, count=5, pexels_key=None, orientation="portrait"):
    downloaded_paths = []
    active_key = pexels_key.strip() if (pexels_key and pexels_key.strip()) else DEFAULT_PEXELS_KEY

    if active_key:
        try:
            headers = {"Authorization": active_key}
            url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orientation}"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for i, photo in enumerate(data.get("photos", [])):
                    img_url = photo["src"]["large2x"]
                    img_data = requests.get(img_url, timeout=10).content
                    filename = f"auto_asset_{i}.jpg"
                    with open(filename, "wb") as f:
                        f.write(img_data)
                    downloaded_paths.append(filename)
                if downloaded_paths:
                    return downloaded_paths
        except Exception:
            pass

    for i in range(count):
        try:
            img_url = f"https://source.unsplash.com/1080x1920/?{query.replace(' ', ',')}&sig={i}"
            res = requests.get(img_url, timeout=10)
            if res.status_code == 200:
                filename = f"auto_asset_unsplash_{i}.jpg"
                with open(filename, "wb") as f:
                    f.write(res.content)
                downloaded_paths.append(filename)
        except Exception:
            continue

    return downloaded_paths


def auto_download_visuals(query, count=5, pexels_key=None, orientation="portrait"):
    return auto_download_visuals_photos(query, count, pexels_key, orientation)


# ==========================================
# 3. CLASS LOGGER UNTUK PROGRESS BAR STREAMLIT
# ==========================================
class StreamlitRenderLogger(ProgressBarLogger):
    def __init__(self, st_progress_bar, st_status_text):
        super().__init__()
        self.st_progress_bar = st_progress_bar
        self.st_status_text = st_status_text

    def callback(self, **changes):
        for k, v in changes.items():
            pass

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 't':
            total = self.bars[bar]['total']
            if total > 0:
                percentage = int((value / total) * 100)
                percentage = min(max(percentage, 0), 100)
                self.st_progress_bar.progress(percentage)
                self.st_status_text.write(f"⏳ **Rendering Video... {percentage}%** ({value}/{total} frame)")


# ==========================================
# 5. GENERATE SKRIP NARASI (GEMINI)
# ==========================================
def generate_script(gemini_key, judul, deskripsi, kategori, gaya_narator, gender_voice, duration_sec):
    client = genai.Client(api_key=gemini_key)
    word_count = int(duration_sec * 2.2)

    prompt = f"""
    Buatkan skrip narasi video yang menarik, runtut, dan profesional.
    - Judul Video: {judul}
    - Deskripsi/Materi: {deskripsi if deskripsi else 'Sesuai judul dan tema'}
    - Kategori Konten: {kategori}
    - Gaya Bahasa Narator: {gaya_narator} (Karakter Suara: {gender_voice})
    - Target Durasi Video: {duration_sec} detik (Maksimal sekitar {word_count} kata).

    Ketentuan Pembuatan Skrip:
    1. Susun narasi secara mengalir dari pendahuluan, isi materi utama, hingga kesimpulan/penutup.
    2. Sesuaikan intonasi dan pilihan kata agar pas dipadukan dengan gaya narator '{gaya_narator}' berkarakter suara {gender_voice}.
    3. HANYA hasilkan teks narasi polos tanpa panggung/petunjuk visual, tanpa instruksi kamera, tanpa label bab/bagian, dan tanpa emoji/karakter khusus.
    """

    models_to_try = ["gemini-3.6-flash", "gemini-1.5-flash"]
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return response.text.strip()
            except (ServerError, APIError):
                time.sleep(1.5)
            except Exception as e:
                raise e

    raise Exception("Gagal terhubung ke Gemini API. Periksa kembali API Key Anda.")


# ==========================================
# 6. GENERATE AUDIO GOOGLE TTS
# ==========================================
def preprocess_text_for_natural_tts(text):
    text = re.sub(r'\b(dan|atau|tetapi|karena|sehingga|bahwa)\b', r', \1', text, flags=re.IGNORECASE)
    text = text.replace(". ", "... ")
    return text


def create_audio_google_tts(text, output_path, gender_key, speed=0.95):
    optimized_text = preprocess_text_for_natural_tts(text)
    lang_code = "id" if gender_key == "Wanita" else "ms"

    temp_raw_audio = "temp_raw_tts.mp3"
    tts = gTTS(text=optimized_text, lang=lang_code, slow=False)
    tts.save(temp_raw_audio)

    try:
        sound = AudioSegment.from_file(temp_raw_audio)
        sound_slowed = sound._spawn(sound.raw_data, overrides={
            "frame_rate": int(sound.frame_rate * speed)
        }).set_frame_rate(sound.frame_rate)

        sound_slowed.export(output_path, format="mp3")

        if os.path.exists(temp_raw_audio):
            os.remove(temp_raw_audio)
    except Exception:
        if os.path.exists(temp_raw_audio):
            os.replace(temp_raw_audio, output_path)


# ==========================================
# 7. EFEK ANIMASI SINEMATIK (ZOOM & PANNING)
# ==========================================
def apply_cinematic_animation(clip, mode="zoom_in"):
    duration = clip.duration
    w, h = clip.size

    def make_frame(t):
        progress = t / duration if duration > 0 else 0

        if mode == "zoom_in":
            scale = 1.0 + (0.15 * progress)
            nw, nh = int(w * scale), int(h * scale)
            frame = clip.get_frame(t)
            import PIL.Image as Image
            img = Image.fromarray(frame).resize((nw, nh), Image.Resampling.LANCZOS)
            left = (nw - w) // 2
            top = (nh - h) // 2
            img = img.crop((left, top, left + w, top + h))
            import numpy as np
            return np.array(img)

        elif mode in ["pan_right", "pan_left"]:
            scale = 1.10
            nw, nh = int(w * scale), int(h * scale)
            frame = clip.get_frame(t)
            import PIL.Image as Image
            img = Image.fromarray(frame).resize((nw, nh), Image.Resampling.LANCZOS)
            max_x = nw - w
            top = (nh - h) // 2
            if mode == "pan_right":
                left = int(max_x * progress)
            else:
                left = int(max_x * (1 - progress))
            img = img.crop((left, top, left + w, top + h))
            import numpy as np
            return np.array(img)

        return clip.get_frame(t)

    try:
        from moviepy.editor import VideoClip
        return VideoClip(make_frame, duration=duration)
    except Exception:
        return clip


# ==========================================
# 8. PROCESS VIDEO GENERATION
# ==========================================
def process_video_generation(visual_paths, custom_audio_path, generated_audio_path, output_path, ratio_type, target_duration, st_progress_bar, st_status_text):
    try:
        from moviepy.editor import AudioFileClip, ImageClip, VideoFileClip, concatenate_videoclips
    except ImportError:
        from moviepy.AudioFileClip import AudioFileClip
        from moviepy.ImageClip import ImageClip
        from moviepy.VideoFileClip import VideoFileClip
        from moviepy.concatenate_videoclips import concatenate_videoclips

    def clip_subclip(clip, start, end):
        return clip.subclipped(start, end) if hasattr(clip, "subclipped") else clip.subclip(start, end)

    def clip_resize(clip, target_size):
        if hasattr(clip, "resized"):
            return clip.resized(target_size)
        elif hasattr(clip, "resize"):
            return clip.resize(newsize=target_size)
        return clip

    def clip_set_audio(clip, audio_clip):
        return clip.with_audio(audio_clip) if hasattr(clip, "with_audio") else clip.set_audio(audio_clip)

    def clip_set_duration(clip, dur):
        return clip.with_duration(dur) if hasattr(clip, "with_duration") else clip.set_duration(dur)

    target_size = (1080, 1920) if ratio_type == "9:16" else (1920, 1080)
    final_audio_path = custom_audio_path if custom_audio_path else generated_audio_path
    audio = AudioFileClip(final_audio_path)

    actual_duration = min(audio.duration, float(target_duration))
    audio = clip_subclip(audio, 0, actual_duration)

    anim_modes = ["zoom_in", "pan_right", "pan_left"]

    clips = []
    if visual_paths:
        raw_clips = []
        total_raw_duration = 0.0

        for i, path in enumerate(visual_paths):
            ext = os.path.splitext(path)[1].lower()
            if ext in [".mp4", ".mov", ".avi"]:
                try:
                    v_clip = VideoFileClip(path)
                    v_clip = clip_resize(v_clip, target_size)

                    if v_clip.duration > 8.0:
                        v_clip = clip_subclip(v_clip, 0, 8.0)

                    raw_clips.append(v_clip)
                    total_raw_duration += v_clip.duration
                except Exception:
                    continue
            else:
                img_clip = ImageClip(path)
                img_clip = clip_set_duration(img_clip, 5.0)
                img_clip = clip_resize(img_clip, target_size)
                anim_style = anim_modes[i % len(anim_modes)]
                img_clip = apply_cinematic_animation(img_clip, mode=anim_style)
                raw_clips.append(img_clip)
                total_raw_duration += 5.0

        if total_raw_duration < actual_duration:
            loop_factor = int(actual_duration // total_raw_duration) + 1
            extended_clips = raw_clips * loop_factor
        else:
            extended_clips = raw_clips

        accumulated_dur = 0.0
        for clip in extended_clips:
            remaining_needed = actual_duration - accumulated_dur
            if remaining_needed <= 0:
                break
            if clip.duration > remaining_needed:
                clipped = clip_subclip(clip, 0, remaining_needed)
                clips.append(clipped)
                accumulated_dur += remaining_needed
            else:
                clips.append(clip)
                accumulated_dur += clip.duration
    else:
        from moviepy.editor import ColorClip
        clip = ColorClip(size=target_size, color=(15, 23, 42), duration=actual_duration)
        clips.append(clip)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video = clip_set_audio(final_video, audio)

    custom_logger = StreamlitRenderLogger(st_progress_bar, st_status_text)

    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger=custom_logger
    )


# ==========================================
# 9. ANTARMUKA APLIKASI (STREAMLIT UI)
# ==========================================
st.title("🎬 AI Studio Video Generator App v10")
st.caption("Video otomatis dengan 3 Mode Voice Over + Background Music + Auto Stock Video 🎙️🎵🎥")

st.subheader("1. Informasi Konten & Topik")
judul = st.text_input("Judul Video *", placeholder="Masukkan judul utama materi...")
deskripsi = st.text_area(
    "Deskripsi / Gambaran Materi (Opsional)",
    placeholder="Jelaskan detail poin penting atau ringkasan materi... (Kosongkan jika ingin upload voice over sendiri)"
)

# ===== MODE DETECTION: VOICE OVER MODE =====
deskripsi_kosong = not deskripsi.strip()
uploaded_vo_file = None

if deskripsi_kosong:
    # ===== MODE 1: UPLOAD VOICE OVER =====
    st.markdown(
        '<div class="info-box">📤 <b>Mode Upload Voice Over Aktif</b><br>'
        'Karena deskripsi kosong, aplikasi akan <b>melewati</b> generate skrip & TTS, '
        'dan langsung menggabungkan file audio voice over yang Anda upload dengan background music.</div>',
        unsafe_allow_html=True
    )
    st.markdown('<span class="vo-badge">MODE 1: UPLOAD VOICE OVER SENDIRI</span>', unsafe_allow_html=True)

    uploaded_vo_file = st.file_uploader(
        "📤 Upload File Voice Over (MP3 / WAV / M4A / OGG)",
        type=["mp3", "wav", "m4a", "ogg"],
        accept_multiple_files=False,
        key="vo_uploader"
    )

    if uploaded_vo_file:
        st.success(f"✅ File VO diterima: **{uploaded_vo_file.name}** ({uploaded_vo_file.size / 1024:.1f} KB)")

    # Set default untuk variabel yang dipakai nanti
    voice_over_mode = "upload"
    voice_over_engine = "none"

else:
    # ===== MODE 2 & 3: GENERATE TTS (pilih engine) =====
    voice_over_mode = "generate"
    st.markdown(
        '<div class="info-box-voice">🎙️ <b>Mode Generate Narasi Otomatis</b><br>'
        'Pilih mesin Text-to-Speech yang akan dipakai untuk membuat narasi dari skrip Gemini.</div>',
        unsafe_allow_html=True
    )

    voice_over_engine = st.radio(
        "🎙️ Pilih Mesin Voice Over:",
        options=[
            "🎙️ Google TTS (100% Gratis, Tanpa Limit)",
            "🎧 ElevenLabs (Gratis, Kuota Terbatas)"
        ],
        index=0,
        horizontal=True,
        key="vo_engine_radio"
    )

    if "Google" in voice_over_engine:
        st.markdown('<span class="google-badge">MODE 2: GOOGLE TTS (GRATIS)</span>', unsafe_allow_html=True)
        st.caption("✅ Google TTS — gratis tanpa limit, kualitas natural, cocok untuk semua jenis video.")
    else:
        st.markdown('<span class="eleven-badge">MODE 3: ELEVENLABS (FREE TIER)</span>', unsafe_allow_html=True)
        st.caption("🎧 ElevenLabs — kualitas suara sangat natural, namun ada kuota bulanan gratis (±10.000 karakter).")

        if not ELEVENLABS_AVAILABLE:
            st.warning("⚠️ Library ElevenLabs belum terinstall. Jalankan: `pip install elevenlabs` untuk mengaktifkan mode ini.")

col_kat, col_gaya, col_gender = st.columns([1, 1, 1])

with col_kat:
    kategori_opt = st.selectbox("Kategori", options=["Pendidikan", "Pengetahuan", "Tutorial", "Sejarah", "Bisnis", "Hiburan", "Input Manual..."])
    kategori = st.text_input("Tuliskan Kategori Khusus:", placeholder="Misal: Hiburan, Bisnis...") if kategori_opt == "Input Manual..." else kategori_opt

with col_gaya:
    gaya_opt = st.selectbox("Gaya Narator", options=["Berita News", "Edukasi", "Presentasi", "Dongeng", "Sejarah", "Input Manual..."])
    gaya_narator = st.text_input("Tuliskan Gaya Narator Khusus:", placeholder="Misal: Santai, Komedi...") if gaya_opt == "Input Manual..." else gaya_opt

with col_gender:
    gender_voice = st.selectbox("Gender Suara Narator", options=["👨 Pria", "👩 Wanita"])
    gender_key = "Pria" if "Pria" in gender_voice else "Wanita"

st.subheader("2. Pengaturan API Key & Audio")
with st.expander("🔑 Kelola API Keys & Suara", expanded=True):
    input_gemini_key = st.text_input("Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")
    input_pexels_key = st.text_input("Pexels API Key (Terpasang)", value=DEFAULT_PEXELS_KEY, type="password")

    # Tampilkan ElevenLabs key hanya jika mode ElevenLabs dipilih
    if voice_over_mode == "generate" and "Eleven" in voice_over_engine:
        input_eleven_key = st.text_input("ElevenLabs API Key", value=DEFAULT_ELEVEN_KEY, type="password")

        if input_eleven_key:
            kuota_info = get_elevenlabs_user_info(input_eleven_key)
            st.info(kuota_info)
    else:
        input_eleven_key = DEFAULT_ELEVEN_KEY

    # Slider kecepatan hanya relevan untuk Google TTS
    if voice_over_mode == "generate" and "Google" in voice_over_engine:
        speech_speed = st.slider("Kecepatan Suara Narator (Google TTS)", min_value=0.80, max_value=1.10, value=0.95, step=0.05)
        st.success("🎉 Voice Over menggunakan Google TTS (100% Gratis & Tanpa Kuota Limit)!")
    elif voice_over_mode == "generate":
        speech_speed = 1.0
        st.caption("ℹ️ ElevenLabs menggunakan kecepatan default (tidak ada slider).")
    else:
        speech_speed = 1.0
        st.info("ℹ️ Slider kecepatan suara dinonaktifkan karena Anda menggunakan file VO sendiri.")

# ==========================================
# 10. SECTION BACKGROUND MUSIC
# ==========================================
st.subheader("3. Background Music Otomatis 🎵")
st.markdown('<span class="music-badge">FITUR v7-v9</span> <span class="upload-badge">MANUAL UPLOAD</span>', unsafe_allow_html=True)

with st.expander("🎼 Pengaturan Background Music", expanded=True):
    enable_bg_music = st.checkbox(
        "Aktifkan Background Music",
        value=True,
        help="Jika dimatikan, video akan hanya berisi narasi tanpa musik."
    )

    music_source = "Otomatis (Gratis & Relevan Topik)"
    uploaded_music_file = None

    if enable_bg_music:
        music_source = st.radio(
            "Sumber Musik:",
            options=[
                "🎵 Otomatis (Gratis & Relevan Topik)",
                "📤 Upload Manual (File Musik Sendiri)"
            ],
            index=0,
            horizontal=True,
            key="music_source_radio"
        )

        if "Otomatis" in music_source:
            st.markdown('<span class="music-badge">MODE: MUSIK OTOMATIS</span>', unsafe_allow_html=True)
            st.caption("🎯 Musik dipilih otomatis dari library gratis (Pixabay Music, CC0) berdasarkan kategori & gaya narator.")

            preview_music = get_music_for_topic(kategori, gaya_narator, deskripsi)
            st.info(f"🎵 **Preview musik terpilih:** *{preview_music['name']}* (mood: {preview_music['mood']})")
        else:
            st.markdown('<span class="upload-badge">MODE: MUSIK UPLOAD MANUAL</span>', unsafe_allow_html=True)
            st.markdown(
                '<div class="info-box-music">📤 <b>Upload File Musik Sendiri</b><br>'
                'Format didukung: MP3, WAV, M4A, OGG, FLAC. '
                'Musik akan otomatis di-loop jika lebih pendek dari narasi, '
                'dan dipotong jika lebih panjang.</div>',
                unsafe_allow_html=True
            )

            uploaded_music_file = st.file_uploader(
                "📤 Upload File Background Music (MP3 / WAV / M4A / OGG / FLAC)",
                type=["mp3", "wav", "m4a", "ogg", "flac"],
                accept_multiple_files=False,
                key="music_uploader"
            )

            if uploaded_music_file:
                st.success(
                    f"✅ File musik diterima: **{uploaded_music_file.name}** "
                    f"({uploaded_music_file.size / 1024:.1f} KB)"
                )

                try:
                    temp_music_preview = "temp_music_preview.mp3"
                    if uploaded_music_file.name.lower().endswith(".mp3"):
                        uploaded_music_file.seek(0)
                        preview_bytes = uploaded_music_file.read()
                        uploaded_music_file.seek(0)
                        with open(temp_music_preview, "wb") as f:
                            f.write(preview_bytes)
                    else:
                        uploaded_music_file.seek(0)
                        audio = AudioSegment.from_file(
                            uploaded_music_file,
                            format=os.path.splitext(uploaded_music_file.name)[1].lstrip(".")
                        )
                        audio.export(temp_music_preview, format="mp3")
                        uploaded_music_file.seek(0)

                    preview_duration = get_audio_duration(temp_music_preview)
                    st.caption(f"⏱️ Durasi musik: **{preview_duration:.1f} detik**")

                    try:
                        os.remove(temp_music_preview)
                    except Exception:
                        pass
                except Exception:
                    st.caption("⏱️ Durasi musik: (tidak bisa dibaca preview)")

    if enable_bg_music:
        col_mus_vol, col_mus_mode = st.columns(2)

        with col_mus_vol:
            music_volume_db = st.slider(
                "Volume Musik (dB relatif terhadap narasi)",
                min_value=-30, max_value=-6, value=-18, step=1,
                help="Semakin negatif = musik semakin pelan. -18 dB direkomendasikan agar narasi dominan."
            )

        with col_mus_mode:
            music_ducking = st.checkbox(
                "Auto-Ducking (Musik mengecil saat narasi bicara)",
                value=True,
                help="Musik otomatis turun volumenya saat ada narasi, sehingga suara narator tetap jelas."
            )

        if "Otomatis" in music_source:
            st.caption("📚 Sumber musik: Pixabay Music (Bebas Royalti / CC0) — aman untuk penggunaan komersial.")
            st.caption(f"🎯 Kategori musik akan dipilih otomatis berdasarkan: **{kategori}** & gaya **{gaya_narator}**")
        else:
            st.caption("📤 Musik: File yang Anda upload — pastikan Anda memiliki hak penggunaan.")
    else:
        music_volume_db = -18.0
        music_ducking = True
        uploaded_music_file = None
        st.info("🔇 Background music dinonaktifkan. Video akan berisi narasi saja.")


# ==========================================
# 11. OPSI BAHAN VISUAL & AUDIO
# ==========================================
st.subheader("4. Opsi Bahan Visual & Audio")
st.markdown('<span class="video-badge">FITUR v8: AUTO VIDEO STOCK</span>', unsafe_allow_html=True)

mode_visual = st.radio(
    "Pilih Mode Pemenuhan Bahan Visual:",
    options=[
        "🌐 Otomatis: Foto + Video Stock (Mix)",
        "📷 Otomatis: Foto Stock Saja",
        "🎥 Otomatis: Video Stock Saja",
        "📁 Manual Upload dari Komputer"
    ],
    index=0
)

uploaded_files = None
search_query = judul

photo_ratio = 0.5
enable_video_download = True

if mode_visual == "📁 Manual Upload dari Komputer":
    uploaded_files = st.file_uploader(
        "Unggah Foto, Video (MP4/MOV), atau Audio",
        type=["jpg", "png", "jpeg", "mp4", "mov", "mp3", "wav"],
        accept_multiple_files=True,
        key="visual_uploader"
    )
elif mode_visual == "📷 Otomatis: Foto Stock Saja":
    enable_video_download = False
    search_query = st.text_input("Kata Kunci Pencarian Gambar Otomatis", value=judul if judul else "nature", key="sq_photo")
elif mode_visual == "🎥 Otomatis: Video Stock Saja":
    enable_video_download = True
    photo_ratio = 0.0
    search_query = st.text_input("Kata Kunci Pencarian Video Otomatis", value=judul if judul else "nature", key="sq_video")
    st.markdown(
        '<div class="info-box-video">🎥 <b>Mode Video Stock Saja</b><br>'
        'Aplikasi akan mengunduh video pendek dari Pexels Videos (gratis). '
        'Setiap video dipotong maksimal 8 detik, lalu disusun otomatis menjadi video utuh. '
        'Jika gagal, akan fallback ke foto stock.</div>',
        unsafe_allow_html=True
    )
else:
    enable_video_download = True
    search_query = st.text_input("Kata Kunci Pencarian (Foto + Video)", value=judul if judul else "nature", key="sq_mix")

    st.markdown(
        '<div class="info-box-video">🎥 <b>Mode Mix: Foto + Video Stock</b><br>'
        'Kombinasi otomatis foto dan video stock gratis dari Pexels. '
        'Atur rasio di bawah ini sesuai preferensi.</div>',
        unsafe_allow_html=True
    )

    photo_ratio = st.slider(
        "Proporsi Foto vs Video",
        min_value=0.0, max_value=1.0, value=0.5, step=0.1,
        help="0.0 = semua video, 0.5 = 50% foto 50% video, 1.0 = semua foto"
    )

    col_pct1, col_pct2 = st.columns(2)
    with col_pct1:
        st.metric("📷 Foto", f"{int(photo_ratio * 100)}%")
    with col_pct2:
        st.metric("🎥 Video", f"{int((1 - photo_ratio) * 100)}%")

col_ratio, col_dur = st.columns(2)
with col_ratio:
    ratio_type = st.selectbox("Aspect Ratio Video", options=["9:16", "16:9"])

with col_dur:
    target_dur_opt = st.selectbox("Target Durasi", options=["<60 detik (Shorts/TikTok)", "3 menit", "5 menit", "8 menit"])
    dur_map = {"<60 detik (Shorts/TikTok)": 50, "3 menit": 180, "5 menit": 300, "8 menit": 480}
    target_duration_sec = dur_map[target_dur_opt]

if "Otomatis" in mode_visual and enable_video_download:
    with st.expander("🎬 Pengaturan Lanjutan Auto Video Stock", expanded=False):
        st.caption("📌 Sumber video: Pexels Videos (gratis, tanpa kuota harian)")
        st.caption("📌 Video otomatis dipotong maksimal 8 detik per klip agar bervariasi")
        st.caption("📌 Video stock akan disusun dengan foto (jika mode Mix) sesuai rasio")

        video_count_target = st.slider(
            "Jumlah aset total yang diunduh",
            min_value=3, max_value=10, value=6, step=1,
            help="Semakin banyak, semakin variatif tapi render lebih lama"
        )
else:
    video_count_target = 5

st.write("")


# ==========================================
# 12. TOMBOL GENERATE & PIPELINE UTAMA
# ==========================================
if st.button("🚀 Generate Full Video (v10)"):
    if not judul:
        st.error("Judul video wajib diisi!")
    elif voice_over_mode == "upload" and not uploaded_vo_file:
        st.error("⚠️ Deskripsi kosong! Wajib upload file Voice Over (MP3/WAV/M4A/OGG) terlebih dahulu.")
    elif voice_over_mode == "generate" and "Eleven" in voice_over_engine and not ELEVENLABS_AVAILABLE:
        st.error("⚠️ Mode ElevenLabs dipilih tapi library belum terinstall. Jalankan: `pip install elevenlabs`")
    elif enable_bg_music and "Upload" in music_source and not uploaded_music_file:
        st.error("⚠️ Mode Upload Musik aktif! Wajib upload file musik (MP3/WAV/M4A/OGG/FLAC) terlebih dahulu.")
    else:
        visual_paths = []
        custom_audio_path = None

        # ==== Ambil visual ====
        if mode_visual == "📁 Manual Upload dari Komputer":
            if uploaded_files:
                for i, file in enumerate(uploaded_files):
                    ext = os.path.splitext(file.name)[1].lower()
                    temp_filename = f"temp_input_{i}{ext}"
                    with open(temp_filename, "wb") as f:
                        f.write(file.read())
                    if ext in [".mp3", ".wav"]:
                        custom_audio_path = temp_filename
                    else:
                        visual_paths.append(temp_filename)
        else:
            orient = "portrait" if ratio_type == "9:16" else "landscape"

            if mode_visual == "📷 Otomatis: Foto Stock Saja":
                st.info(f"📷 Mengunduh {video_count_target} foto HD dari Pexels: '{search_query}'...")
                with st.spinner("Mengunduh foto stock..."):
                    visual_paths = auto_download_visuals_photos(
                        query=search_query, count=video_count_target,
                        pexels_key=input_pexels_key, orientation=orient
                    )
                if visual_paths:
                    st.success(f"✅ Berhasil mengunduh {len(visual_paths)} foto")
                else:
                    st.warning("⚠️ Gagal mengunduh foto. Menggunakan warna latar belakang standar.")

            elif mode_visual == "🎥 Otomatis: Video Stock Saja":
                st.info(f"🎥 Mengunduh {video_count_target} video stock dari Pexels: '{search_query}'...")
                with st.spinner("Mengunduh video stock (butuh waktu ±30-60 detik)..."):
                    stats = {"photos": 0, "videos": 0, "failed": 0}
                    visual_paths, stats = auto_download_visuals_mixed(
                        query=search_query, total_count=video_count_target,
                        photo_ratio=0.0, pexels_key=input_pexels_key,
                        orientation=orient, enable_video=True
                    )
                if visual_paths:
                    st.success(f"✅ Berhasil: {stats['videos']} video, {stats['photos']} foto (fallback)")
                else:
                    st.warning("⚠️ Gagal mengunduh video. Menggunakan warna latar belakang standar.")

            else:
                st.info(f"🌐 Mengunduh campuran foto + video stock dari Pexels: '{search_query}'...")
                with st.spinner("Mengunduh aset (butuh waktu ±30-60 detik)..."):
                    visual_paths, stats = auto_download_visuals_mixed(
                        query=search_query, total_count=video_count_target,
                        photo_ratio=photo_ratio, pexels_key=input_pexels_key,
                        orientation=orient, enable_video=True
                    )
                if visual_paths:
                    st.success(
                        f"✅ Berhasil: **{stats['photos']} foto** + **{stats['videos']} video** "
                        f"(total {len(visual_paths)} aset)"
                    )
                    if stats['failed'] > 0:
                        st.caption(f"ℹ️ {stats['failed']} aset gagal diunduh dan di-skip.")
                else:
                    st.warning("⚠️ Gagal mengunduh aset. Menggunakan warna latar belakang standar.")

        try:
            narration_audio_path = None

            # ==========================================
            # CABANG 1: MODE UPLOAD VOICE OVER SENDIRI
            # ==========================================
            if voice_over_mode == "upload":
                st.info("📤 1. Memproses file Voice Over yang diupload...")
                narration_audio_path = save_uploaded_voice_over(uploaded_vo_file, "temp_uploaded_vo.mp3")
                vo_duration = get_audio_duration(narration_audio_path)

                target_duration_sec = int(vo_duration)
                st.success(f"✅ File VO berhasil diproses! Durasi: **{vo_duration:.1f} detik**")
                st.info(f"ℹ️ Target durasi video otomatis disesuaikan dengan durasi VO = **{target_duration_sec} detik**")

            # ==========================================
            # CABANG 2: MODE GENERATE TTS (Google atau ElevenLabs)
            # ==========================================
            else:
                st.info("📝 1. Memformulasi skrip narasi sesuai tema, durasi, dan gender suara...")
                script = generate_script(
                    gemini_key=input_gemini_key, judul=judul, deskripsi=deskripsi,
                    kategori=kategori, gaya_narator=gaya_narator, gender_voice=gender_key, duration_sec=target_duration_sec
                )
                st.success("📝 **Skrip Narasi Berhasil Dibuat:**")
                st.write(f"_{script}_")

                generated_audio_path = "temp_generated_audio.mp3"
                if not custom_audio_path:
                    # ==== Google TTS ====
                    if "Google" in voice_over_engine:
                        st.info(f"🎙️ 2. Menggenerasi narasi suara dengan **Google TTS** ({gender_voice})...")
                        create_audio_google_tts(
                            text=script, output_path=generated_audio_path,
                            gender_key=gender_key, speed=speech_speed
                        )
                        narration_audio_path = generated_audio_path

                    # ==== ElevenLabs ====
                    else:
                        st.info(f"🎧 2. Menggenerasi narasi suara dengan **ElevenLabs** ({gender_voice}, gaya {gaya_narator})...")
                        try:
                            create_audio_elevenlabs(
                                eleven_key=input_eleven_key, text=script,
                                output_path=generated_audio_path,
                                gender_key=gender_key, gaya_narator=gaya_narator
                            )
                            narration_audio_path = generated_audio_path
                            st.success("✅ Narasi ElevenLabs berhasil dibuat!")
                        except Exception as e:
                            st.error(f"⚠️ ElevenLabs gagal: {str(e)}")
                            st.warning("🔄 Fallback otomatis ke Google TTS...")
                            create_audio_google_tts(
                                text=script, output_path=generated_audio_path,
                                gender_key=gender_key, speed=0.95
                            )
                            narration_audio_path = generated_audio_path
                else:
                    st.info("🎵 Menggunakan file audio buatan/unggahan pengguna...")
                    narration_audio_path = custom_audio_path

            # ==========================================
            # BACKGROUND MUSIC MIXING
            # ==========================================
            final_audio_for_video = narration_audio_path

            if enable_bg_music and narration_audio_path:
                if "Otomatis" in music_source:
                    st.info("🎼 3. Menyiapkan background music otomatis yang relevan dengan topik...")
                    with st.spinner("Memilih & mengunduh musik background gratis..."):
                        mixed_audio_path, music_info = auto_background_music_pipeline(
                            narration_audio_path=narration_audio_path,
                            kategori=kategori, gaya_narator=gaya_narator, deskripsi=deskripsi,
                            output_path="temp_mixed_audio_v10.mp3",
                            music_volume_db=music_volume_db
                        )

                    if music_info:
                        st.success(f"🎵 **Background music otomatis berhasil:** *{music_info['name']}* (mood: {music_info['mood']})")
                        st.caption(f"Volume musik: {music_volume_db} dB | Auto-ducking: {'Aktif ✅' if music_ducking else 'Nonaktif ❌'}")
                        final_audio_for_video = mixed_audio_path
                    else:
                        st.warning("⚠️ Gagal mengunduh/memproses musik otomatis. Video akan dibuat tanpa musik.")
                        final_audio_for_video = narration_audio_path
                else:
                    st.info("🎼 3. Memproses background music dari file yang Anda upload...")
                    with st.spinner("Mencampur musik dengan narasi..."):
                        mixed_audio_path, music_info = manual_background_music_pipeline(
                            narration_audio_path=narration_audio_path,
                            uploaded_music_file=uploaded_music_file,
                            output_path="temp_mixed_audio_manual_v10.mp3",
                            music_volume_db=music_volume_db,
                            ducking=music_ducking
                        )

                    if music_info:
                        st.success(f"🎵 **Background music manual berhasil:** *{music_info['name']}*")
                        st.caption(f"Volume musik: {music_volume_db} dB | Auto-ducking: {'Aktif ✅' if music_ducking else 'Nonaktif ❌'}")
                        final_audio_for_video = mixed_audio_path
                    else:
                        st.warning("⚠️ Gagal memproses musik manual. Video akan dibuat tanpa musik.")
                        final_audio_for_video = narration_audio_path

            st.info("📹 4. Merender video MP4 dengan animasi sinematik & indikator progress...")

            st_status_text = st.empty()
            st_progress_bar = st.progress(0)

            output_video_path = "hasil_preview_app_v10.mp4"
            process_video_generation(
                visual_paths=visual_paths,
                custom_audio_path=None,
                generated_audio_path=final_audio_for_video,
                output_path=output_video_path,
                ratio_type=ratio_type,
                target_duration=target_duration_sec,
                st_progress_bar=st_progress_bar,
                st_status_text=st_status_text
            )

            st_progress_bar.progress(100)
            st_status_text.write("✅ **Proses Render Selesai (100%)**")

            st.success("✨ Video MP4 Siap Dipreview & Diunduh!")
            st.video(output_video_path)

            with open(output_video_path, "rb") as file:
                st.download_button(
                    label="📥 Unduh Video (MP4)",
                    data=file,
                    file_name=f"{judul.replace(' ', '_')}_v10.mp4",
                    mime="video/mp4"
                )

        except Exception as e:
            st.error(f"Terjadi Kendala: {str(e)}")