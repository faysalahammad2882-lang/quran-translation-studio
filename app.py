import streamlit as st
import re
import io
import asyncio
from pydub import AudioSegment

st.set_page_config(
    page_title="Quran Voice Translation Studio",
    page_icon="📖",
    layout="wide"
)

st.title("📖 Quran Voice Translation Studio")
st.caption("Version 0.3 | Audio + Video Upload")

st.info(
    "Audio অথবা Video আপলোড করুন। "
    "এরপর QuranCaption SRT দিয়ে অনুবাদের ভয়েস তৈরি করুন।"
)

# SRT READER
def parse_srt(raw):
    content = raw.decode("utf-8-sig", errors="replace")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", content.strip())
    cues = []

    for block in blocks:
        lines = [x.strip() for x in block.split("\n") if x.strip()]
        timing_index = next(
            (i for i, x in enumerate(lines) if "-->" in x),
            None
        )

        if timing_index is None or timing_index + 1 >= len(lines):
            continue

        match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
            r"(\d{2}:\d{2}:\d{2}[,.]\d{3})",
            lines[timing_index]
        )

        if not match:
            continue

        def to_ms(value):
            h, m, rest = value.replace(",", ".").split(":")
            s, ms = rest.split(".")
            return (
                (int(h)*3600 + int(m)*60 + int(s))*1000
                + int(ms)
            )

        start = to_ms(match.group(1))
        end = to_ms(match.group(2))

        if end > start:
            cues.append({
                "entry": len(cues) + 1,
                "start": start,
                "end": end,
                "arabic": " ".join(lines[timing_index+1:])
            })

    return cues


def format_time(ms):
    h, r = divmod(int(ms), 3600000)
    m, r = divmod(r, 60000)
    s, ms = divmod(r, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# TEXT TO SPEECH
async def create_voice(text, voice, rate):
    import edge_tts

    communicator = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate
    )

    chunks = []

    async for chunk in communicator.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])

    if not chunks:
        raise RuntimeError("Voice audio পাওয়া যায়নি।")

    return b"".join(chunks)


# UPLOAD MODE
mode = st.radio(
    "১. Upload Type নির্বাচন করুন",
    ["Audio Upload", "Video Upload"],
    horizontal=True
)

if mode == "Audio Upload":
    source = st.file_uploader(
        "মূল তিলাওয়াতের অডিও",
        type=["mp3", "wav", "m4a", "ogg", "flac", "aac"]
    )
    is_video = False

else:
    source = st.file_uploader(
        "তিলাওয়াতসহ ভিডিও",
        type=["mp4", "mov", "mkv", "webm", "avi"]
    )
    is_video = True


if source:
    st.success("ফাইল আপলোড হয়েছে: " + source.name)

    if is_video:
        st.video(source.getvalue())
    else:
        st.audio(source.getvalue())


# SRT UPLOAD
srt_file = st.file_uploader(
    "২. QuranCaption SRT আপলোড করুন",
    type=["srt", "txt"]
)

if srt_file:

    cues = parse_srt(srt_file.getvalue())

    if not cues:
        st.error("SRT ফাইল পড়া যায়নি।")
        st.stop()

    st.success(f"{len(cues)}টি Subtitle Entry পাওয়া গেছে।")

    st.warning(
        "একটি আয়াত একাধিক Subtitle Entry-তে ভাগ হতে পারে। "
        "সঠিক আয়াত নম্বর যাচাই করুন। এই সংস্করণে প্রতিটি Entry "
        "আলাদাভাবে প্রসেস হবে।"
    )

    # LANGUAGE
    language = st.radio(
        "৩. Translation Language",
        ["বাংলা", "English"],
        horizontal=True
    )

    if language == "বাংলা":
        voices = {
            "বাংলা নারী": "bn-BD-NabanitaNeural",
            "বাংলা পুরুষ": "bn-BD-PradeepNeural",
            "বাংলা ভারতীয় নারী": "bn-IN-TanishaaNeural",
            "বাংলা ভারতীয় পুরুষ": "bn-IN-BashkarNeural"
        }

    else:
        voices = {
            "English Female": "en-US-JennyNeural",
            "English Male": "en-US-GuyNeural",
            "English UK Female": "en-GB-SoniaNeural",
            "English UK Male": "en-GB-RyanNeural"
        }

    voice_name = st.selectbox(
        "৪. Voice নির্বাচন করুন",
        list(voices.keys())
    )

    selected_voice = voices[voice_name]

    speed = st.select_slider(
        "Voice Speed",
        ["ধীর", "স্বাভাবিক", "দ্রুত"],
        value="স্বাভাবিক"
    )

    rate = {
        "ধীর": "-10%",
        "স্বাভাবিক": "+0%",
        "দ্রুত": "+10%"
    }[speed]

    pause = st.slider(
        "Translation-এর পরে বিরতি (ms)",
        0, 3000, 700, 100
    )

    # TRANSLATIONS
    st.subheader("৫. Translation Text")

    translations = []

    for cue in cues:

        with st.expander(
            f"Entry {cue['entry']} | "
            f"{format_time(cue['start'])}"
        ):

            st.markdown("**Arabic:** " + cue["arabic"])

            ayah = st.number_input(
                "আয়াত নম্বর",
                min_value=1,
                max_value=286,
                value=min(cue["entry"], 7),
                key=f"ayah_{cue['entry']}"
            )

            text = st.text_area(
                f"{language} Translation",
                key=f"translation_{cue['entry']}",
                height=90
            )

            translations.append({
                "cue": cue,
                "ayah": int(ayah),
                "text": text.strip()
            })

    st.caption(
        "অনুবাদ নির্ভুলভাবে যাচাই করে লিখুন। "
        "এখনো স্বয়ংক্রিয় Translation Import যুক্ত হয়নি।"
    )

    # GENERATE
    if st.button(
        "৬. Generate Translation Voice",
        type="primary",
        disabled=source is None
    ):

        if not all(x["text"] for x in translations):
            st.error("সব Translation Text পূরণ করুন।")

        else:
            try:
                with st.spinner("Audio প্রস্তুত হচ্ছে..."):

                    file_bytes = source.getvalue()
                    extension = source.name.rsplit(".", 1)[-1].lower()

                    try:
                        original = AudioSegment.from_file(
                            io.BytesIO(file_bytes),
                            format=extension
                        )
                    except Exception:
                        original = AudioSegment.from_file(
                            io.BytesIO(file_bytes)
                        )

                if len(original) == 0:
                    raise RuntimeError("অডিও পাওয়া যায়নি।")

                final_audio = AudioSegment.empty()

                progress = st.progress(0)
                status = st.empty()

                for index, item in enumerate(translations):

                    cue = item["cue"]

                    start = max(
                        0,
                        min(cue["start"], len(original))
                    )

                    end = max(
                        0,
                        min(cue["end"], len(original))
                    )

                    if end <= start:
                        raise ValueError(
                            f"Entry {cue['entry']} এর Timing ভুল।"
                        )

                    status.write(
                        f"Voice তৈরি হচ্ছে: "
                        f"{index+1}/{len(translations)}"
                    )

                    voice_bytes = asyncio.run(
                        create_voice(
                            item["text"],
                            selected_voice,
                            rate
                        )
                    )

                    translated = AudioSegment.from_file(
                        io.BytesIO(voice_bytes),
                        format="mp3"
                    )

                    recitation = original[start:end]

                    final_audio += (
                        recitation
                        + AudioSegment.silent(duration=250)
                        + translated
                        + AudioSegment.silent(duration=pause)
                    )

                    progress.progress(
                        (index+1)/len(translations)
                    )

                # MP3 EXPORT
                output = io.BytesIO()

                final_audio.export(
                    output,
                    format="mp3",
                    bitrate="192k"
                )

                result = output.getvalue()

                st.success("Translation MP3 তৈরি হয়েছে!")

                st.audio(result, format="audio/mp3")

                st.download_button(
                    "Download MP3",
                    data=result,
                    file_name="quran_translation.mp3",
                    mime="audio/mpeg"
                )

            except Exception as error:

                st.error(f"Processing Error: {error}")

                st.info(
                    "FFmpeg, ইন্টারনেট এবং Voice Service "
                    "সঠিকভাবে কাজ করছে কি না পরীক্ষা করুন।"
                )

elif source:
    st.info("QuranCaption SRT ফাইল আপলোড করুন।")

st.divider()

st.caption(
    "Prototype v0.3 | Video upload থেকে MP3 তৈরি হয়। "
    "ভিডিওতে নতুন Voice বসিয়ে MP4 Export এখনো যুক্ত হয়নি।"
    )
