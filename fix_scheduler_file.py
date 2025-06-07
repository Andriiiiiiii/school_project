# fix_scheduler_file.py
def fix_scheduler():
    """Автоматически исправляет функцию process_daily_reset в services/scheduler.py"""
    
    try:
        # Читаем текущий файл
        with open('services/scheduler.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print("📖 Читаем services/scheduler.py...")
        
        # Ищем начало функции process_daily_reset
        start_line = None
        end_line = None
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def process_daily_reset(chat_id):'):
                start_line = i
                print(f"✅ Найдена функция process_daily_reset на строке {i+1}")
                break
        
        if start_line is None:
            print("❌ Функция process_daily_reset не найдена")
            return False
        
        # Ищем конец функции (следующая функция или конец файла)
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            # Если строка не пустая и не комментарий, и имеет такой же или меньший отступ
            if line.strip() and not line.strip().startswith('#'):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and (line.strip().startswith('def ') or 
                                                      line.strip().startswith('class ') or
                                                      line.strip().startswith('if __name__')):
                    end_line = i
                    break
        
        if end_line is None:
            end_line = len(lines)
        
        print(f"📍 Функция занимает строки {start_line+1}-{end_line}")
        
        # Новая исправленная функция
        new_function = '''def process_daily_reset(chat_id):
    """Ежедневный сброс данных пользователя с ИСПРАВЛЕННОЙ обработкой streak."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        reset_key = f"{chat_id}_reset_{today}"
        
        # Проверка на повторный сброс
        if hasattr(process_daily_reset, 'processed_resets') and reset_key in process_daily_reset.processed_resets:
            return
            
        if not hasattr(process_daily_reset, 'processed_resets'):
            process_daily_reset.processed_resets = set()
        
        # ИСПРАВЛЕННАЯ логика проверки и сброса дней подряд
        try:
            from database.crud import get_user_streak, reset_user_streak
            streak, last_test_date = get_user_streak(chat_id)
            
            if streak > 0:
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                logger.debug(f"Checking streak for user {chat_id}: streak={streak}, last_test_date={last_test_date}, yesterday={yesterday}")
                
                should_reset = False
                reset_reason = ""
                
                if not last_test_date:
                    # Нет записи о последнем тесте - сбрасываем
                    should_reset = True
                    reset_reason = "no_test_date"
                elif last_test_date < yesterday:
                    # Последний тест был позавчера или раньше - сбрасываем
                    should_reset = True
                    reset_reason = f"test_too_old_{last_test_date}"
                elif last_test_date == yesterday:
                    # Тест был вчера - НЕ сбрасываем
                    should_reset = False
                    reset_reason = "test_yesterday_ok"
                elif last_test_date == today:
                    # Тест уже был сегодня - НЕ сбрасываем
                    should_reset = False
                    reset_reason = "test_today_ok"
                else:
                    # Дата в будущем (не должно быть) - сбрасываем
                    should_reset = True
                    reset_reason = f"future_date_{last_test_date}"
                
                if should_reset:
                    logger.info(f"Resetting streak for user {chat_id}: reason={reset_reason}, old_streak={streak}")
                    reset_user_streak(chat_id)
                    
                    # Если нужно уведомить пользователя о сбросе streak (опционально)
                    if not PRODUCTION_MODE:
                        logger.info(f"DEBUG: User {chat_id} streak reset from {streak} to 0. Reason: {reset_reason}")
                else:
                    logger.debug(f"Keeping streak for user {chat_id}: reason={reset_reason}, streak={streak}")
                    
        except Exception as e:
            logger.error(f"Ошибка проверки streak для пользователя {chat_id}: {e}")
        
        # Обработка leftover слов (существующая логика)
        if chat_id in daily_words_cache:
            entry = daily_words_cache[chat_id]
            unique_words = entry[8] if len(entry) > 8 and entry[8] else []
            is_revision = entry[9] if len(entry) > 9 else False
            
            # Сохраняем leftover слова ТОЛЬКО если это НЕ режим повторения
            if not is_revision and unique_words:
                try:
                    learned_raw = crud.get_learned_words(chat_id)
                    learned_set = set(extract_english(item[0]).lower() for item in learned_raw)
                    
                    # Фильтруем только действительно невыученные слова
                    leftover_words = []
                    for word in unique_words:
                        english_part = extract_english(word).lower()
                        if english_part and english_part not in learned_set:
                            leftover_words.append(word)
                    
                    # Сохраняем leftover слова для следующего дня
                    if leftover_words:
                        previous_daily_words[chat_id] = leftover_words
                        if not PRODUCTION_MODE:
                            logger.info(f"Saved {len(leftover_words)} leftover words for user {chat_id}")
                    elif chat_id in previous_daily_words:
                        del previous_daily_words[chat_id]
                        
                except Exception as e:
                    logger.error("Ошибка обработки leftover слов для пользователя %s: %s", chat_id, e)
            else:
                # В режиме повторения не сохраняем leftover слова
                if chat_id in previous_daily_words:
                    del previous_daily_words[chat_id]
                
            # Сбрасываем кэш слов дня
            reset_daily_words_cache(chat_id)
        
        # Сброс напоминания о тесте
        if chat_id in test_reminder_sent:
            del test_reminder_sent[chat_id]
        
        process_daily_reset.processed_resets.add(reset_key)
        
        # Очистка старых записей
        if len(process_daily_reset.processed_resets) > 1000:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            today_check = datetime.now().strftime("%Y-%m-%d")
            process_daily_reset.processed_resets = {
                key for key in process_daily_reset.processed_resets 
                if today_check in key or yesterday in key
            }
            
        if not PRODUCTION_MODE:
            logger.info("Ежедневный сброс выполнен для пользователя %s", chat_id)
            
    except Exception as e:
        logger.error("Ошибка ежедневного сброса для пользователя %s: %s", chat_id, e)

'''
        
        # Заменяем старую функцию на новую
        new_lines = lines[:start_line] + [new_function] + lines[end_line:]
        
        # Записываем обновленный файл
        with open('services/scheduler.py', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print("✅ Функция process_daily_reset обновлена успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🔧 ИСПРАВЛЕНИЕ ФУНКЦИИ process_daily_reset")
    print("=" * 50)
    
    if fix_scheduler():
        print("\n🎉 ФУНКЦИЯ ОБНОВЛЕНА!")
        print("\n📋 СЛЕДУЮЩИЙ ШАГ:")
        print("   python debug_streak_system.py")
    else:
        print("\n❌ ОШИБКА ПРИ ОБНОВЛЕНИИ")
        print("   Обновите функцию вручную")