# Quran Voice Translation Studio — Prototype v0.1

Android-friendly Streamlit prototype.

## What it does
- Accepts original recitation audio and QuranCaption SRT.
- Parses cue numbers, timestamps, and Arabic text.
- Lets the user select Bangla or English TTS voice.
- Lets the user enter/verify a translation for each cue.
- Generates a sequential MP3: recitation cue -> translation voice -> pause.

## Important limitations
- Does not automatically identify Surah/Ayah.
- Does not automatically fetch translations.
- User must verify translations and map subtitle entries to ayah numbers.
- Current prototype speaks after every SRT cue. If one ayah spans multiple cues, combine those cues in a future version before generating one translation.
- Edge TTS is a free online service, not a guaranteed permanent API. Internet is required.
- This is a prototype, not a finished production app.

## Streamlit Community Cloud
- Main file: `app.py`
- Python dependencies: `requirements.txt`
- System dependency: `packages.txt` (ffmpeg)
