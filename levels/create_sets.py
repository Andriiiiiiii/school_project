#!/usr/bin/env python3
import os
from pathlib import Path

# Определяем, какие файлы нужно создать в каждой папке
SETS_MAP = {
    "A1": [
        "A1 TOEFL 1", "A1 TOEFL 2", "A1 TOEFL 3",
        "A1 ЕГЭ 1", "A1 ЕГЭ 2", "A1 ЕГЭ 3"
    ],
    "A2": [
        "A2 TOEFL 1", "A2 TOEFL 2", "A2 TOEFL 3",
        "A2 ЕГЭ 1", "A2 ЕГЭ 2", "A2 ЕГЭ 3"
    ],
    "B1": [
        "B1 TOEFL 1", "B1 TOEFL 2", "B1 TOEFL 3",
        "B1 ЕГЭ 1", "B1 ЕГЭ 2", "B1 ЕГЭ 3"
    ],
    "B2": [
        "B2 TOEFL 1", "B2 TOEFL 2", "B2 TOEFL 3",
        "B2 ЕГЭ 1", "B2 ЕГЭ 2", "B2 ЕГЭ 3"
    ],
    "C1": [
        "C1 TOEFL 1", "C1 TOEFL 2", "C1 TOEFL 3",
        "C1 ЕГЭ 1", "C1 ЕГЭ 2", "C1 ЕГЭ 3"
    ],
    "C2": [
        "C2 TOEFL 1", "C2 TOEFL 2", "C2 TOEFL 3",
        "C2 ЕГЭ 1", "C2 ЕГЭ 2", "C2 ЕГЭ 3"
    ],
}

def main():
    cwd = Path.cwd()
    for level, sets in SETS_MAP.items():
        level_dir = cwd / level
        if not level_dir.is_dir():
            print(f"Папка не найдена: {level_dir}, пропускаем...")
            continue
        for set_name in sets:
            file_path = level_dir / f"{set_name}.txt"
            if file_path.exists():
                print(f"Уже есть: {file_path}")
            else:
                file_path.touch()
                print(f"Создано: {file_path}")

if __name__ == "__main__":
    main()

