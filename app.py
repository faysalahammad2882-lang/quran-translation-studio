import streamlit as st
import re, io, asyncio, tempfile, os
from pydub import AudioSegment

st.set_page_config(page_title="Quran Voice Translation Studio", page_icon="📖", layout="wide")
st.title("📖 Quran Voice Translation Studio")
st.caption("Prototype v0.1 — QuranCaption SRT + recitation audio + translation voice")

st.info(
    "এই সংস্করণে QuranCaption থেকে Export করা SRT ও মূল অডিও নিয়ে প্রতিটি Subtitle Entry-এর জন্য "
    "অনুবাদ লিখে বাংলা/ইংরেজি TTS তৈরি করা যায়। এটি এখনো স্বয়ংক্রিয়ভাবে ৯টি cue-কে ৭টি আয়াতে "
    "মিলিয়ে দেয় না; ভুল অনুবাদ এড়াতে mapping ব্যবহারকারী যাচাই করবেন।"
)

def parse_srt(content):
    content = content.decode("utf-8-sig", errors="replace") if isinstance(content, bytes) else content
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", content.strip())
    items = []
    for block in blocks:
        lines = [x.strip() for x in block.split("\n") if x.strip()]
        if len(lines) < 3:
            continue
        timing_idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_idx is None:
            continue
        timing = lines[timing_idx]
        m = re.match(r"\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})", timing)
        if not m:
            continue
        def ms(ts):
            h, minute, rest = ts.replace(",", ".").split(":")
            sec, milli = rest.split(".")
            return ((int(h)*3600 + int(minute)*60 + int(sec))*1000 + int(milli))
        text = " ".join(lines[timing_idx+1:])
        items.append({"index": len(items)+1, "start_ms": ms(m.group(1)), "end_ms": ms(m.group(2)), "arabic": text})
    return items

def to_srt_time(ms):
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{milli:03}"

async def edge_tts_bytes(text, voice, rate):
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)

def run_tts(text, voice, rate):
    return asyncio.run(edge_tts_bytes(text, voice, rate))

audio_file = st.file_uploader("১) মূল তিলাওয়াতের অডিও আপলোড করুন", type=["mp3","wav","m4a","ogg"])
srt_file = st.file_uploader("২) QuranCaption থেকে Export করা SRT আপলোড করুন", type=["srt","txt"])

if srt_file:
    cues = parse_srt(srt_file.getvalue())
    if not cues:
        st.error("SRT পড়া যায়নি। UTF-8 SRT ফাইলটি আবার Export করে দিন।")
    else:
        st.success(f"{len(cues)}টি Subtitle Entry পাওয়া গেছে।")
        st.caption("প্রতিটি Entry-র সময় ও আরবি লেখা দেখুন। একাধিক Entry একই আয়াতের অংশ হলে আগে মিলিয়ে নিন।")
        language = st.radio("৩) অনুবাদের ভাষা নির্বাচন করুন", ["বাংলা", "English"], horizontal=True)
        if language == "বাংলা":
            voice_options = {
                "বাংলা নারী — সোফিয়া": "bn-BD-NabanitaNeural",
                "বাংলা পুরুষ — প্রদীপ": "bn-BD-PradeepNeural",
                "বাংলা (ভারত) — নারী": "bn-IN-TanishaaNeural",
                "বাংলা (ভারত) — পুরুষ": "bn-IN-BashkarNeural",
            }
        else:
            voice_options = {
                "English US — Jenny (Female)": "en-US-JennyNeural",
                "English US — Guy (Male)": "en-US-GuyNeural",
                "English UK — Sonia (Female)": "en-GB-SoniaNeural",
                "English UK — Ryan (Male)": "en-GB-RyanNeural",
            }
        voice_label = st.selectbox("৪) AI Voice নির্বাচন করুন", list(voice_options.keys()))
        voice = voice_options[voice_label]
        rate_label = st.select_slider("ভয়েসের গতি", options=["ধীর","স্বাভাবিক","দ্রুত"], value="স্বাভাবিক")
        rate = {"ধীর":"-10%","স্বাভাবিক":"+0%","দ্রুত":"+10%"}[rate_label]
        pause = st.slider("অনুবাদের পরে বিরতি (মিলিসেকেন্ড)", 0, 3000, 700, 100)
        st.subheader("৫) প্রতিটি Subtitle Entry-এর অনুবাদ লিখুন")
        st.warning("এই পরীক্ষামূলক সংস্করণে অনুবাদ স্বয়ংক্রিয়ভাবে বসানো হচ্ছে না। নির্ভুল অনুবাদ যাচাই করে লিখুন বা পেস্ট করুন।")
        translations = []
        for cue in cues:
            with st.expander(f"Entry {cue['index']} · {to_srt_time(cue['start_ms'])} – {to_srt_time(cue['end_ms'])}", expanded=(cue["index"] <= 2)):
                st.markdown(f"**আরবি টেক্সট:** {cue['arabic']}")
                ayah = st.number_input(f"এটি কোন আয়াতের অংশ? (Entry {cue['index']})", min_value=1, max_value=286, value=min(cue["index"], 7), key=f"ayah_{cue['index']}")
                tr = st.text_area(f"{language} translation", key=f"tr_{cue['index']}", height=90, placeholder="যাচাইকৃত অনুবাদ এখানে লিখুন…")
                translations.append({"cue":cue, "ayah":int(ayah), "text":tr.strip()})
        st.caption("একই আয়াতের একাধিক Entry থাকলে একই আয়াত নম্বর দিন। Prototype প্রতিটি Entry-র পর ভয়েস বসাবে; পরের সংস্করণে একই আয়াতের Entry একত্র করে একবার অনুবাদ দেওয়ার সুবিধা যোগ হবে।")

        if st.button("৬) Translation Voice তৈরি করুন", type="primary", disabled=not audio_file):
            if not all(x["text"] for x in translations):
                st.error("সব Entry-এর অনুবাদ পূরণ করুন।")
            else:
                try:
                    original = AudioSegment.from_file(io.BytesIO(audio_file.getvalue()))
                    final_audio = AudioSegment.empty()
                    progress = st.progress(0)
                    status = st.empty()
                    for i, item in enumerate(translations):
                        cue = item["cue"]
                        start = min(cue["start_ms"], len(original))
                        end = min(cue["end_ms"], len(original))
                        if end <= start:
                            raise ValueError(f"Entry {i+1}-এর সময় অডিওর দৈর্ঘ্যের বাইরে বা ভুল।")
                        recitation = original[start:end]
                        status.write(f"Entry {i+1}/{len(translations)} — ভয়েস তৈরি হচ্ছে…")
                        tts_data = run_tts(item["text"], voice, rate)
                        spoken = AudioSegment.from_file(io.BytesIO(tts_data), format="mp3")
                        final_audio += recitation + AudioSegment.silent(duration=250) + spoken + AudioSegment.silent(duration=pause)
                        progress.progress((i+1)/len(translations))
                    st.success("অনুবাদসহ অডিও তৈরি হয়েছে।")
                    mp3 = io.BytesIO()
                    final_audio.export(mp3, format="mp3", bitrate="192k")
                    st.audio(mp3.getvalue(), format="audio/mp3")
                    st.download_button("MP3 ডাউনলোড করুন", data=mp3.getvalue(), file_name="quran_translation_mix.mp3", mime="audio/mpeg")
                except Exception as e:
                    st.error(f"অডিও তৈরি করা যায়নি: {e}")
                    st.info("TTS-এর জন্য ইন্টারনেট সংযোগ প্রয়োজন। Edge TTS বিনামূল্যের অনলাইন ভয়েস সার্ভিস; এটি কোনো স্থায়ী API নিশ্চয়তা নয়।")
else:
    st.markdown("**শুরু করতে:** প্রথমে মূল তিলাওয়াতের অডিও এবং QuranCaption-এর SRT ফাইল আপলোড করুন।")

st.divider()
st.caption("Prototype v0.1 · এটি এখনো পূর্ণাঙ্গ QuranCaption বিকল্প নয়। অনুবাদ ও আয়াত-ম্যাপিং ব্যবহারকারীকে যাচাই করতে হবে।")
