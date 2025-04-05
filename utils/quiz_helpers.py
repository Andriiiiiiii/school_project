# utils/quiz_helpers.py
"""
Файл: utils/quiz_helpers.py
Описание: Функция для загрузки данных для квиза.
"""

import os
import logging
from config import LEVELS_DIR, DEFAULT_SETS

# Настройка логирования
logger = logging.getLogger(__name__)

def load_quiz_data(level: str, chosen_set: str = None):
    """
    Загружает данные для квиза для указанного уровня.
    """
    try:
        # Если выбранный сет не указан, берем основной по умолчанию для уровня
        if chosen_set is None:
            chosen_set = DEFAULT_SETS.get(level)
            if not chosen_set:
                logger.warning(f"No default set defined for level {level}")
                return []
        
        # Формируем имя файла с учетом выбранного сета
        filename = os.path.join(LEVELS_DIR, level, f"{chosen_set}.txt")
        
        if not os.path.exists(filename):
            logger.warning(f"Quiz file not found: {filename}")
            return []
            
        quiz_items = []
        try:
            with open(filename, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Проверяем различные форматы разделителей
                    word = None
                    translation = None
                    
                    for separator in [" - ", " – ", ": "]:
                        if separator in line:
                            parts = line.split(separator, 1)
                            if len(parts) == 2:
                                word = parts[0].strip()
                                translation = parts[1].strip()
                                quiz_items.append({"word": word, "translation": translation})
                                break
                    
                    # Если не нашли разделитель, но строка выглядит как слово,
                    # добавляем ее как есть (это поможет с совместимостью)
                    if word is None and line and not line.startswith(("#", "//")):
                        quiz_items.append({"word": line, "translation": line})
            
            logger.debug(f"Loaded {len(quiz_items)} quiz items from {filename}")
            return quiz_items
        except UnicodeDecodeError:
            logger.warning(f"Unicode decode error in file {filename}, trying with cp1251 encoding")
            try:
                with open(filename, encoding="cp1251") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Повторяем ту же логику для другой кодировки
                        word = None
                        translation = None
                        
                        for separator in [" - ", " – ", ": "]:
                            if separator in line:
                                parts = line.split(separator, 1)
                                if len(parts) == 2:
                                    word = parts[0].strip()
                                    translation = parts[1].strip()
                                    quiz_items.append({"word": word, "translation": translation})
                                    break
                        
                        if word is None and line and not line.startswith(("#", "//")):
                            quiz_items.append({"word": line, "translation": line})
                
                logger.debug(f"Loaded {len(quiz_items)} quiz items from {filename} with cp1251 encoding")
                return quiz_items
            except Exception as e:
                logger.error(f"Failed to load file with alternative encoding: {e}")
                return []
    except FileNotFoundError:
        logger.error(f"Quiz file not found: {filename}")
        return []
    except PermissionError:
        logger.error(f"Permission denied when accessing quiz file: {filename}")
        return []
    except Exception as e:
        logger.error(f"Error loading quiz data for level {level}, set {chosen_set}: {e}")
        return []