# utils/helpers.py
import os
import random
from config import LEVELS_DIR

def load_words_for_level(level: str):
    filename = os.path.join(LEVELS_DIR, f"{level}.txt")
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return words


