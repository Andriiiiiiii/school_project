# services/text_to_speech.py
import os
import tempfile
from gtts import gTTS

def generate_speech(text, lang="en"):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tf:
        filename = tf.name
        tts = gTTS(text=text, lang=lang)
        tts.save(filename)
    return filename
