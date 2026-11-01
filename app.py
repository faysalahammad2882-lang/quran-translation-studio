import io
import json
import requests
import streamlit as st
from pydub import AudioSegment

st.set_page_config(
    page_title="Quran Translation Studio",
    page_icon="📖",
    layout="centered"
)

st.title("📖 Quran Translation Studio")
st.caption("Heart of The Quran Tv")

st.markdown("""
### Welcome to Quran Translation Studio
Upload Quran recitation and prepare Bangla translation audio
ayah by ayah.
""")

st.info(
    "Prototype v1: প্রথম সংস্করণে প্রতিটি আয়াতের সময় "
    "ও যাচাইকৃত বাংলা অনুবাদ নিজে দিতে হবে।"
)

# AUDIO UPLOAD
st.header("1. Upload Quran Audio")

audio_file = st.file_uploader(
    "Upload MP3, WAV, M4A or OGG",
    type=["mp3", "wav", "m4a", "ogg"]
)

# SURAH INFORMATION
st.header("2. Surah Information")

surah_name = st.text_input(
    "Surah Name",
    value="Al-Kahf"
)

st.caption("প্রথম পরীক্ষার জন্য Surah Al-Kahf নির্বাচন করা হয়েছে।")

# AYAH DATA
st.header("3. Ayah Timing and Translation")

sample_data = [
    {
        "ayah": 1,
        "start": 0.0,
        "end": 12.5,
        "translation": "এখানে প্রথম আয়াতের যাচাইকৃত বাংলা অনুবাদ লিখুন।"
    },
    {
        "ayah": 2,
        "start": 12.5,
        "end": 24.0,
        "translation": "এখানে দ্বিতীয় আয়াতের যাচাইকৃত বাংলা অনুবাদ লিখুন।"
    }
]

ayah_json = st.text_area(
    "Ayah Data (JSON)",
    value=json.dumps(sample_data, ensure_ascii=False, indent=2),
    height=260
)

st.caption(
    "Start এবং End সময় সেকেন্ডে দিতে হবে। "
    "সময় মূল অডিওর শুরু থেকে গণনা করতে হবে।"
)

# VOICE SETTINGS
st.header("4. Your Cloned Voice")

api_key = st.text_input(
    "ElevenLabs API Key",
    type="password"
)

voice_id = st.text_input(
    "ElevenLabs Voice ID"
)

model_id = st.text_input(
    "Voice Model ID",
    value="eleven_multilingual_v2"
)

st.caption(
    "ElevenLabs-এ নিজের কণ্ঠের অনুমোদিত Voice Clone তৈরি করে "
    "তার API Key এবং Voice ID এখানে দিন।"
)

# AUDIO SETTINGS
st.header("5. Audio Settings")

gap = st.slider(
    "Pause after Quran recitation (seconds)",
    0.0, 3.0, 0.7, 0.1
)

translation_gap = st.slider(
    "Pause after Bangla translation (seconds)",
    0.0, 3.0, 0.5, 0.1
)


def generate_voice(text):
    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        + voice_id
    )

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.80
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=180
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Voice generation failed: "
            + response.text[:500]
        )

    return AudioSegment.from_file(
        io.BytesIO(response.content),
        format="mp3"
    )


# GENERATE AUDIO
st.header("6. Generate Quran Translation Audio")

if st.button(
    "🎬 Generate Audio",
    type="primary",
    use_container_width=True
):

    if audio_file is None:
        st.error("Please upload Quran audio first.")

    elif not api_key or not voice_id:
        st.error("Please enter your ElevenLabs API Key and Voice ID.")

    else:
        try:
            rows = json.loads(ayah_json)

            if not isinstance(rows, list) or not rows:
                raise ValueError("Ayah JSON must be a non-empty list.")

            extension = audio_file.name.rsplit(".", 1)[-1].lower()

            original_audio = AudioSegment.from_file(
                io.BytesIO(audio_file.getvalue()),
                format=extension
            )

            final_audio = AudioSegment.empty()
            previous_end = 0.0

            progress = st.progress(0)
            status = st.empty()

            for index, item in enumerate(rows):

                ayah_number = item["ayah"]
                start = float(item["start"])
                end = float(item["end"])
                translation = str(item["translation"]).strip()

                if start < previous_end:
                    raise ValueError(
                        f"Ayah {ayah_number}: overlapping timing."
                    )

                if end <= start or end * 1000 > len(original_audio):
                    raise ValueError(
                        f"Ayah {ayah_number}: invalid timing."
                    )

                if not translation or "এখানে" in translation:
                    raise ValueError(
                        f"Ayah {ayah_number}: add verified translation."
                    )

                # Preserve audio between marked ayahs
                if start > previous_end:
                    final_audio += original_audio[
                        int(previous_end * 1000):
                        int(start * 1000)
                    ]

                # Original Quran recitation
                recitation = original_audio[
                    int(start * 1000):
                    int(end * 1000)
                ]

                status.write(
                    f"Creating Bangla voice for Ayah {ayah_number}..."
                )

                # Generate cloned voice
                bangla_voice = generate_voice(translation)

                # Ayah -> pause -> translation -> pause
                final_audio += recitation
                final_audio += AudioSegment.silent(
                    duration=int(gap * 1000)
                )
                final_audio += bangla_voice
                final_audio += AudioSegment.silent(
                    duration=int(translation_gap * 1000)
                )

                previous_end = end
                progress.progress((index + 1) / len(rows))

            # Add remaining original audio
            if previous_end * 1000 < len(original_audio):
                final_audio += original_audio[
                    int(previous_end * 1000):
                ]

            output = io.BytesIO()

            final_audio.export(
                output,
                format="mp3",
                bitrate="192k"
            )

            st.success("Your audio is ready!")

            st.audio(
                output.getvalue(),
                format="audio/mp3"
            )

            st.download_button(
                "⬇️ Download Final MP3",
                data=output.getvalue(),
                file_name="Quran_Bangla_Translation.mp3",
                mime="audio/mpeg",
                use_container_width=True
            )

            status.success("Audio generation completed.")

        except Exception as error:
            st.error(str(error))


st.divider()

st.markdown("""
**Heart of The Quran Tv**

May Allah bless this project.

⚠️ Always verify Quran ayah timing and Bangla translation
before publishing.
""")
