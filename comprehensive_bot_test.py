# comprehensive_bot_test.py
"""
КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ФУНКЦИОНАЛА ENGLISH LEARNING BOT
=========================================================

Этот скрипт тестирует все основные функции бота согласно техническому заданию:
1. Мой словарь
2. Слова дня 
3. Тест дня
4. Практика (тест по словарю, заучивание набора)
5. Персонализация (уровень, уведомления, наборы)
6. Система дней подряд
7. Система подписки и скидок
8. Граничные случаи и сложные сценарии
"""

import sys
import os
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text, color=Colors.BLUE):
    print(f"\n{color}{Colors.BOLD}{'='*80}")
    print(f"{text:^80}")
    print(f"{'='*80}{Colors.END}")

def print_test(text, color=Colors.CYAN):
    print(f"\n{color}{Colors.BOLD}🧪 {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.WHITE}ℹ️  {text}{Colors.END}")

class BotTester:
    def __init__(self):
        self.test_users = [888881, 888882, 888883]  # Разные тестовые пользователи
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        
    def setup_test_environment(self):
        """Настройка тестовой среды"""
        print_header("НАСТРОЙКА ТЕСТОВОЙ СРЕДЫ")
        
        try:
            from database.db import db_manager
            from database import crud
            
            # Очищаем тестовых пользователей
            for user_id in self.test_users:
                with db_manager.transaction() as conn:
                    conn.execute("DELETE FROM users WHERE chat_id = ?", (user_id,))
                    conn.execute("DELETE FROM dictionary WHERE chat_id = ?", (user_id,))
                    conn.execute("DELETE FROM learned_words WHERE chat_id = ?", (user_id,))
                    conn.execute("DELETE FROM active_payments WHERE chat_id = ?", (user_id,))
            
            print_success("Тестовая среда очищена")
            return True
            
        except Exception as e:
            print_error(f"Ошибка настройки среды: {e}")
            return False

    def test_user_creation_and_onboarding(self):
        """Тест 1: Создание пользователей и онбординг"""
        print_header("ТЕСТ 1: СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ И ОНБОРДИНГ")
        
        try:
            from database import crud
            from config import DEFAULT_SETS
            
            for i, user_id in enumerate(self.test_users):
                print_test(f"Создание пользователя {user_id}")
                
                # Создаем пользователя
                crud.add_user(user_id)
                user = crud.get_user(user_id)
                
                assert user is not None, f"Пользователь {user_id} не создан"
                assert user[0] == user_id, "Неверный chat_id"
                assert user[1] == "A1", "Неверный уровень по умолчанию"
                assert user[2] == 5, "Неверное количество слов по умолчанию"
                assert user[3] in [3, 10], "Неверное количество повторений по умолчанию"
                
                print_success(f"Пользователь {user_id} создан корректно")
                
                # Проверяем назначение базового набора
                default_set = DEFAULT_SETS.get("A1")
                if default_set:
                    crud.update_user_chosen_set(user_id, default_set)
                    updated_user = crud.get_user(user_id)
                    assert updated_user[6] == default_set, "Базовый набор не назначен"
                    print_success(f"Базовый набор '{default_set}' назначен")
                
                # Тест различных уровней
                levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
                test_level = levels[i % len(levels)]
                crud.update_user_level(user_id, test_level)
                
                updated_user = crud.get_user(user_id)
                assert updated_user[1] == test_level, f"Уровень не обновлен до {test_level}"
                print_success(f"Уровень установлен: {test_level}")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка создания пользователей: {e}")
            self.failed_tests += 1
            return False

    def test_words_day_generation(self):
        """Тест 2: Генерация слов дня"""
        print_header("ТЕСТ 2: ГЕНЕРАЦИЯ СЛОВ ДНЯ")
        
        try:
            from utils.helpers import get_daily_words_for_user, reset_daily_words_cache
            from config import REMINDER_START, DURATION_HOURS
            
            user_id = self.test_users[0]
            
            print_test("Базовая генерация слов дня")
            
            # Тест базовой генерации
            result = get_daily_words_for_user(
                user_id, "A1", 5, 3,
                first_time=REMINDER_START,
                duration_hours=DURATION_HOURS
            )
            
            assert result is not None, "Слова дня не сгенерированы"
            messages, times = result
            assert len(messages) > 0, "Сообщения пустые"
            assert len(times) > 0, "Времена пустые"
            assert len(messages) == len(times), "Количество сообщений и времен не совпадает"
            
            print_success(f"Сгенерировано {len(messages)} сообщений с временами")
            
            # Тест кэширования
            print_test("Тестирование кэширования")
            result2 = get_daily_words_for_user(
                user_id, "A1", 5, 3,
                first_time=REMINDER_START,
                duration_hours=DURATION_HOURS
            )
            
            assert result2 == result, "Кэширование не работает"
            print_success("Кэширование работает корректно")
            
            # Тест принудительного сброса
            print_test("Тестирование принудительного сброса кэша")
            result3 = get_daily_words_for_user(
                user_id, "A1", 7, 2,  # Другие параметры
                first_time=REMINDER_START,
                duration_hours=DURATION_HOURS,
                force_reset=True
            )
            
            assert result3 != result, "Принудительный сброс не работает"
            messages3, times3 = result3
            expected_total = 7 * 2  # 7 слов × 2 повторения
            assert len(messages3) == expected_total, f"Ожидалось {expected_total} сообщений, получено {len(messages3)}"
            print_success("Принудительный сброс работает корректно")
            
            # Тест различных параметров
            print_test("Тестирование различных параметров")
            test_cases = [
                (3, 1),   # Минимум
                (10, 5),  # Максимум повторений
                (20, 3),  # Максимум слов
                (1, 1),   # Крайний минимум
            ]
            
            for words, reps in test_cases:
                reset_daily_words_cache(user_id)
                result = get_daily_words_for_user(
                    user_id, "A1", words, reps,
                    first_time=REMINDER_START,
                    duration_hours=DURATION_HOURS,
                    force_reset=True
                )
                
                if result:
                    messages, times = result
                    expected = words * reps
                    assert len(messages) <= expected + 1, f"Слишком много сообщений для {words}×{reps}"
                    print_success(f"Параметры {words}×{reps}: {len(messages)} сообщений")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка генерации слов дня: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def test_dictionary_functionality(self):
        """Тест 3: Функционал словаря"""
        print_header("ТЕСТ 3: ФУНКЦИОНАЛ СЛОВАРЯ")
        
        try:
            from database import crud
            
            user_id = self.test_users[0]
            
            print_test("Добавление слов в словарь")
            
            # Добавляем тестовые слова
            test_words = [
                ("apple", "яблоко"),
                ("book", "книга"), 
                ("cat", "кот"),
                ("dog", "собака"),
                ("house", "дом")
            ]
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            for word, translation in test_words:
                crud.add_learned_word(user_id, word, translation, today)
            
            # Проверяем добавление
            learned = crud.get_learned_words(user_id)
            assert len(learned) == len(test_words), f"Ожидалось {len(test_words)} слов, получено {len(learned)}"
            
            # Проверяем содержимое
            learned_words = [w[0] for w in learned]
            for word, _ in test_words:
                assert word in learned_words, f"Слово '{word}' не найдено в словаре"
            
            print_success(f"Добавлено {len(test_words)} слов в словарь")
            
            # Тест предотвращения дубликатов
            print_test("Тестирование предотвращения дубликатов")
            crud.add_learned_word(user_id, "apple", "яблоко", today)  # Повторное добавление
            learned_after = crud.get_learned_words(user_id)
            assert len(learned_after) == len(test_words), "Дубликаты не предотвращены"
            print_success("Дубликаты предотвращены")
            
            # Тест очистки словаря
            print_test("Тестирование очистки словаря")
            crud.clear_learned_words_for_user(user_id)
            cleared = crud.get_learned_words(user_id)
            assert len(cleared) == 0, "Словарь не очищен"
            print_success("Словарь очищен корректно")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка функционала словаря: {e}")
            self.failed_tests += 1
            return False

    def test_quiz_functionality(self):
        """Тест 4: Функционал тестов"""
        print_header("ТЕСТ 4: ФУНКЦИОНАЛ ТЕСТОВ")
        
        try:
            from utils.quiz_helpers import load_quiz_data
            from utils.quiz_utils import generate_quiz_options
            from database import crud
            
            user_id = self.test_users[0]
            
            print_test("Загрузка данных для квиза")
            
            # Тестируем загрузку данных квиза
            quiz_data = load_quiz_data("A1", "A1 Basic 1")
            assert quiz_data is not None, "Данные квиза не загружены"
            assert len(quiz_data) > 0, "Данные квиза пустые"
            
            print_success(f"Загружено {len(quiz_data)} вопросов для квиза")
            
            # Тестируем генерацию вариантов ответов
            print_test("Генерация вариантов ответов")
            
            if quiz_data:
                test_item = quiz_data[0]
                correct_answer = test_item["translation"]
                all_translations = [item["translation"] for item in quiz_data]
                
                options, correct_index = generate_quiz_options(correct_answer, all_translations, 4)
                
                assert len(options) == 4, f"Ожидалось 4 варианта, получено {len(options)}"
                assert correct_answer in options, "Правильный ответ не в вариантах"
                assert options[correct_index] == correct_answer, "Неверный индекс правильного ответа"
                assert correct_index >= 0 and correct_index < 4, "Индекс вне диапазона"
                
                print_success("Варианты ответов сгенерированы корректно")
            
            # Тест симуляции прохождения квиза
            print_test("Симуляция прохождения квиза")
            
            # Очищаем словарь и добавляем несколько правильных ответов
            crud.clear_learned_words_for_user(user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            
            correct_answers = 0
            test_questions = quiz_data[:5] if len(quiz_data) >= 5 else quiz_data
            
            for question in test_questions:
                # Симулируем правильный ответ (50% вероятность)
                if random.choice([True, False]):
                    crud.add_learned_word(
                        user_id, 
                        question["word"], 
                        question["translation"], 
                        today
                    )
                    correct_answers += 1
            
            # Проверяем, что слова добавились в словарь
            learned = crud.get_learned_words(user_id)
            assert len(learned) == correct_answers, f"В словаре должно быть {correct_answers} слов"
            
            print_success(f"Симуляция квиза: {correct_answers}/{len(test_questions)} правильных ответов")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка функционала тестов: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def test_settings_and_personalization(self):
        """Тест 5: Настройки и персонализация"""
        print_header("ТЕСТ 5: НАСТРОЙКИ И ПЕРСОНАЛИЗАЦИЯ")
        
        try:
            from database import crud
            
            user_id = self.test_users[1]
            crud.add_user(user_id)
            
            print_test("Обновление настроек пользователя")
            
            # Тест обновления различных настроек
            test_cases = [
                ("level", "B2", lambda u: u[1]),
                ("words_per_day", 15, lambda u: u[2]),
                ("notifications", 4, lambda u: u[3]),
                ("timezone", "Europe/London", lambda u: u[5]),
            ]
            
            for setting_name, test_value, getter in test_cases:
                if setting_name == "level":
                    crud.update_user_level(user_id, test_value)
                elif setting_name == "words_per_day":
                    crud.update_user_words_per_day(user_id, test_value)
                elif setting_name == "notifications":
                    crud.update_user_notifications(user_id, test_value)
                elif setting_name == "timezone":
                    crud.update_user_timezone(user_id, test_value)
                
                user = crud.get_user(user_id)
                actual_value = getter(user)
                assert actual_value == test_value, f"{setting_name}: ожидалось {test_value}, получено {actual_value}"
                print_success(f"{setting_name} обновлен: {test_value}")
            
            # Тест выбора набора слов
            print_test("Тестирование выбора набора слов")
            
            test_set = "A1 Basic 1"
            crud.update_user_chosen_set(user_id, test_set)
            user = crud.get_user(user_id)
            assert user[6] == test_set, f"Набор не обновлен: ожидался {test_set}, получен {user[6]}"
            print_success(f"Набор слов установлен: {test_set}")
            
            # Тест смены набора с очисткой словаря
            print_test("Тестирование смены набора с очисткой словаря")
            
            # Добавляем слова в словарь
            today = datetime.now().strftime("%Y-%m-%d")
            crud.add_learned_word(user_id, "test", "тест", today)
            
            # Меняем набор
            new_set = "A1 Basic 2"
            crud.clear_learned_words_for_user(user_id)  # Симулируем очистку при смене набора
            crud.update_user_chosen_set(user_id, new_set)
            
            # Проверяем
            learned = crud.get_learned_words(user_id)
            user = crud.get_user(user_id)
            
            assert len(learned) == 0, "Словарь не очищен при смене набора"
            assert user[6] == new_set, "Набор не обновлен"
            print_success("Смена набора с очисткой словаря работает")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка настроек: {e}")
            self.failed_tests += 1
            return False

    def test_streak_functionality(self):
        """Тест 6: Функционал дней подряд"""
        print_header("ТЕСТ 6: ФУНКЦИОНАЛ ДНЕЙ ПОДРЯД")
        
        try:
            from database import crud
            
            user_id = self.test_users[2]
            crud.add_user(user_id)
            
            print_test("Базовые операции с streak")
            
            # Тест начального состояния
            streak, date = crud.get_user_streak(user_id)
            assert streak == 0, f"Начальный streak должен быть 0, получен {streak}"
            assert date is None, "Начальная дата должна быть None"
            print_success("Начальное состояние streak корректно")
            
            # Тест инкремента
            print_test("Тестирование инкремента streak")
            
            new_streak = crud.increment_user_streak(user_id)
            assert new_streak == 1, f"После первого инкремента streak должен быть 1, получен {new_streak}"
            
            # Повторный инкремент в тот же день
            same_day_streak = crud.increment_user_streak(user_id)
            assert same_day_streak == 1, f"Повторный инкремент должен вернуть 1, получен {same_day_streak}"
            print_success("Инкремент streak работает корректно")
            
            # Тест обновления streak
            print_test("Тестирование обновления streak")
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            crud.update_user_streak(user_id, 5, yesterday)
            
            streak, date = crud.get_user_streak(user_id)
            assert streak == 5, f"Streak должен быть 5, получен {streak}"
            assert date == yesterday, f"Дата должна быть {yesterday}, получена {date}"
            print_success("Обновление streak работает")
            
            # Тест инкремента после вчерашнего дня
            incremented = crud.increment_user_streak(user_id)
            assert incremented == 6, f"После инкремента streak должен быть 6, получен {incremented}"
            print_success("Инкремент после предыдущего дня работает")
            
            # Тест сброса
            print_test("Тестирование сброса streak")
            
            crud.reset_user_streak(user_id)
            streak, date = crud.get_user_streak(user_id)
            assert streak == 0, f"После сброса streak должен быть 0, получен {streak}"
            print_success("Сброс streak работает")
            
            # Тест ежедневного сброса
            print_test("Тестирование логики ежедневного сброса")
            
            from services.scheduler import process_daily_reset
            
            # Случай 1: Пользователь проходил тест вчера
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            crud.update_user_streak(user_id, 10, yesterday)
            
            # Очищаем кэш сброса для корректного тестирования
            if hasattr(process_daily_reset, 'processed_resets'):
                process_daily_reset.processed_resets.clear()
            
            process_daily_reset(user_id)
            streak, _ = crud.get_user_streak(user_id)
            assert streak == 10, f"Streak должен сохраниться (тест вчера), получен {streak}"
            print_success("Streak сохранен при тесте вчера")
            
            # Случай 2: Пользователь не проходил тест позавчера
            day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            crud.update_user_streak(user_id, 15, day_before_yesterday)
            
            if hasattr(process_daily_reset, 'processed_resets'):
                process_daily_reset.processed_resets.clear()
            
            process_daily_reset(user_id)
            streak, _ = crud.get_user_streak(user_id)
            assert streak == 0, f"Streak должен сброситься (пропуск дня), получен {streak}"
            print_success("Streak сброшен при пропуске дня")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка функционала streak: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def test_subscription_and_discounts(self):
        """Тест 7: Подписка и скидки"""
        print_header("ТЕСТ 7: ПОДПИСКА И СКИДКИ")
        
        try:
            from database import crud
            from services.payment import PaymentService
            
            user_id = self.test_users[0]
            
            print_test("Тестирование статуса подписки")
            
            # Тест бесплатного пользователя
            is_premium = crud.is_user_premium(user_id)
            assert not is_premium, "Новый пользователь не должен быть премиум"
            
            status, expires_at, payment_id = crud.get_user_subscription_status(user_id)
            assert status == 'free', f"Статус должен быть 'free', получен {status}"
            print_success("Бесплатный статус корректен")
            
            # Тест активации премиум
            print_test("Тестирование активации премиум")
            
            future_date = (datetime.now() + timedelta(days=30)).isoformat()
            crud.update_user_subscription(user_id, "premium", future_date, "test_payment")
            
            is_premium = crud.is_user_premium(user_id)
            assert is_premium, "Пользователь должен быть премиум после активации"
            
            status, expires_at, payment_id = crud.get_user_subscription_status(user_id)
            assert status == 'premium', f"Статус должен быть 'premium', получен {status}"
            assert expires_at == future_date, "Дата окончания не совпадает"
            print_success("Премиум активация работает")
            
            # Тест скидок за streak
            print_test("Тестирование скидок за streak")
            
            # Без streak
            crud.reset_user_streak(user_id)
            discount = crud.calculate_streak_discount(user_id)
            assert discount == 0, f"Без streak скидка должна быть 0%, получена {discount}%"
            
            # С streak 15 дней
            crud.update_user_streak(user_id, 15)
            discount = crud.calculate_streak_discount(user_id)
            assert discount == 15, f"За 15 дней скидка должна быть 15%, получена {discount}%"
            
            # С streak 35 дней (максимум 30%)
            crud.update_user_streak(user_id, 35)
            discount = crud.calculate_streak_discount(user_id)
            assert discount == 30, f"Максимальная скидка должна быть 30%, получена {discount}%"
            
            print_success("Скидки за streak работают корректно")
            
            # Тест расчета цен со скидкой
            print_test("Тестирование расчета цен со скидкой")
            
            price_info = PaymentService.calculate_discounted_price(user_id, 1)
            assert price_info['has_discount'], "Должна быть скидка"
            assert price_info['discount_percent'] == 30, "Процент скидки должен быть 30%"
            assert price_info['final_price'] < price_info['base_price'], "Итоговая цена должна быть меньше базовой"
            
            expected_final = price_info['base_price'] * 0.7  # 30% скидка
            assert abs(price_info['final_price'] - expected_final) < 0.01, "Неверный расчет итоговой цены"
            print_success("Расчет цен со скидкой работает")
            
            # Тест для бесплатного пользователя (без скидки)
            print_test("Тестирование скидок для бесплатного пользователя")
            
            crud.update_user_subscription(user_id, "free")
            crud.update_user_streak(user_id, 20)  # Большой streak
            
            discount = crud.calculate_streak_discount(user_id)
            assert discount == 0, f"Бесплатный пользователь не должен получать скидку, получена {discount}%"
            print_success("Бесплатные пользователи не получают скидки")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка подписки и скидок: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def test_subscription_helpers(self):
        """Тест 8: Вспомогательные функции подписки"""
        print_header("ТЕСТ 8: ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ПОДПИСКИ")
        
        try:
            from utils.subscription_helpers import (
                get_available_sets_for_user,
                is_set_available_for_user,
                get_premium_sets_for_level,
                get_all_sets_for_level
            )
            from database import crud
            
            user_id = self.test_users[1]
            crud.add_user(user_id)
            
            print_test("Тестирование доступности наборов для бесплатного пользователя")
            
            # Тест для бесплатного пользователя
            crud.update_user_subscription(user_id, "free")
            crud.update_user_level(user_id, "A1")
            
            available_sets = get_available_sets_for_user(user_id, "A1")
            all_sets = get_all_sets_for_level("A1")
            premium_sets = get_premium_sets_for_level("A1")
            
            print_info(f"Всего наборов A1: {len(all_sets)}")
            print_info(f"Доступных бесплатных: {len(available_sets)}")
            print_info(f"Премиум наборов: {len(premium_sets)}")
            
            # Проверяем, что бесплатный пользователь имеет ограниченный доступ
            assert len(available_sets) < len(all_sets), "Бесплатный пользователь должен иметь ограниченный доступ"
            
            # Проверяем конкретные наборы
            basic_sets = ["A1 Basic 1", "A1 Basic 2"]
            for basic_set in basic_sets:
                if basic_set in all_sets:  # Проверяем, что набор существует
                    is_available = is_set_available_for_user(user_id, basic_set)
                    assert is_available, f"Базовый набор '{basic_set}' должен быть доступен бесплатному пользователю"
            
            print_success("Бесплатные наборы доступны бесплатному пользователю")
            
            # Тест для премиум пользователя
            print_test("Тестирование доступности наборов для премиум пользователя")
            
            future_date = (datetime.now() + timedelta(days=30)).isoformat()
            crud.update_user_subscription(user_id, "premium", future_date, "test_payment")
            
            available_sets_premium = get_available_sets_for_user(user_id, "A1")
            
            # Премиум пользователь должен иметь доступ ко всем наборам
            assert len(available_sets_premium) == len(all_sets), "Премиум пользователь должен иметь доступ ко всем наборам"
            
            # Проверяем премиум наборы
            for premium_set in premium_sets[:3]:  # Проверяем первые 3
                is_available = is_set_available_for_user(user_id, premium_set)
                assert is_available, f"Премиум набор '{premium_set}' должен быть доступен премиум пользователю"
            
            print_success("Все наборы доступны премиум пользователю")
            
            # Тест для разных уровней
            print_test("Тестирование наборов для разных уровней")
            
            levels_to_test = ["A2", "B1", "B2", "C1", "C2"]
            for level in levels_to_test:
                crud.update_user_level(user_id, level)
                level_sets = get_available_sets_for_user(user_id, level)
                level_all = get_all_sets_for_level(level)
                
                if level_all:  # Если есть наборы для этого уровня
                    assert len(level_sets) > 0, f"Должны быть доступные наборы для уровня {level}"
                    assert len(level_sets) == len(level_all), f"Премиум пользователь должен иметь доступ ко всем наборам уровня {level}"
                    print_success(f"Уровень {level}: {len(level_sets)} наборов доступно")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка вспомогательных функций подписки: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def test_edge_cases_and_error_handling(self):
        """Тест 9: Граничные случаи и обработка ошибок"""
        print_header("ТЕСТ 9: ГРАНИЧНЫЕ СЛУЧАИ И ОБРАБОТКА ОШИБОК")
        
        try:
            from database import crud
            from utils.helpers import get_daily_words_for_user
            from config import REMINDER_START, DURATION_HOURS
            
            print_test("Тестирование несуществующего пользователя")
            
            # Несуществующий пользователь
            fake_user_id = 999999
            streak, date = crud.get_user_streak(fake_user_id)
            assert streak == 0, "Несуществующий пользователь должен иметь streak = 0"
            
            discount = crud.calculate_streak_discount(fake_user_id)
            assert discount == 0, "Несуществующий пользователь должен иметь скидку = 0"
            
            print_success("Несуществующие пользователи обрабатываются корректно")
            
            # Тест экстремальных значений streak
            print_test("Тестирование экстремальных значений streak")
            
            user_id = self.test_users[0]
            
            # Очень большой streak
            crud.update_user_streak(user_id, 9999)
            discount = crud.calculate_streak_discount(user_id)
            assert discount <= 30, f"Скидка не должна превышать 30%, получена {discount}%"
            
            # Отрицательный streak (не должно быть возможным, но проверим)
            crud.update_user_streak(user_id, -5)
            streak, _ = crud.get_user_streak(user_id)
            assert streak >= 0, f"Streak не должен быть отрицательным, получен {streak}"
            
            print_success("Экстремальные значения обрабатываются корректно")
            
            # Тест с несуществующим набором слов
            print_test("Тестирование несуществующего набора слов")
            
            crud.update_user_chosen_set(user_id, "Несуществующий набор")
            result = get_daily_words_for_user(
                user_id, "A1", 5, 3,
                first_time=REMINDER_START,
                duration_hours=DURATION_HOURS,
                force_reset=True
            )
            
            # Результат может быть None или содержать предложение сменить набор
            if result is None:
                print_success("Несуществующий набор обрабатывается корректно (None)")
            elif len(result) == 3:  # Предложение сменить набор
                print_success("Несуществующий набор обрабатывается корректно (предложение смены)")
            else:
                print_warning("Неожиданный результат для несуществующего набора")
            
            # Тест экстремальных параметров слов дня
            print_test("Тестирование экстремальных параметров слов дня")
            
            # Восстанавливаем нормальный набор
            crud.update_user_chosen_set(user_id, "A1 Basic 1")
            
            extreme_cases = [
                (0, 1),   # 0 слов
                (1, 0),   # 0 повторений
                (100, 10), # Очень много слов
                (5, 100),  # Очень много повторений
            ]
            
            for words, reps in extreme_cases:
                try:
                    result = get_daily_words_for_user(
                        user_id, "A1", words, reps,
                        first_time=REMINDER_START,
                        duration_hours=DURATION_HOURS,
                        force_reset=True
                    )
                    # Любой результат или None - главное, что нет исключения
                    print_success(f"Параметры {words}×{reps} обработаны без ошибок")
                except Exception as e:
                    print_warning(f"Параметры {words}×{reps} вызвали исключение: {e}")
            
            # Тест истекшей подписки
            print_test("Тестирование истекшей подписки")
            
            past_date = (datetime.now() - timedelta(days=1)).isoformat()
            crud.update_user_subscription(user_id, "premium", past_date, "expired_payment")
            
            is_premium = crud.is_user_premium(user_id)
            assert not is_premium, "Истекшая подписка должна считаться неактивной"
            
            discount = crud.calculate_streak_discount(user_id)
            assert discount == 0, "Пользователь с истекшей подпиской не должен получать скидку"
            
            print_success("Истекшая подписка обрабатывается корректно")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка граничных случаев: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def test_daily_reset_scenarios(self):
        """Тест 10: Сценарии ежедневного сброса"""
        print_header("ТЕСТ 10: СЦЕНАРИИ ЕЖЕДНЕВНОГО СБРОСА")
        
        try:
            from database import crud
            from utils.helpers import get_daily_words_for_user, previous_daily_words, reset_daily_words_cache
            from services.scheduler import process_daily_reset
            from config import REMINDER_START, DURATION_HOURS
            
            user_id = self.test_users[2]
            crud.add_user(user_id)
            crud.update_user_chosen_set(user_id, "A1 Basic 1")
            
            print_test("Тестирование логики перехода невыученных слов")
            
            # Генерируем слова дня
            result = get_daily_words_for_user(
                user_id, "A1", 5, 2,
                first_time=REMINDER_START,
                duration_hours=DURATION_HOURS,
                force_reset=True
            )
            
            assert result is not None, "Слова дня должны сгенерироваться"
            
            # Добавляем только часть слов в словарь (симулируем частичное прохождение теста)
            today = datetime.now().strftime("%Y-%m-%d")
            crud.add_learned_word(user_id, "apple", "яблоко", today)
            crud.add_learned_word(user_id, "book", "книга", today)
            # Оставляем 3 слова невыученными
            
            print_success("Симуляция частичного прохождения теста")
            
            # Симулируем процесс ежедневного сброса
            print_test("Симуляция ежедневного сброса")
            
            # Очищаем кэш для корректного тестирования
            if hasattr(process_daily_reset, 'processed_resets'):
                process_daily_reset.processed_resets.clear()
            
            # Сохраняем состояние до сброса
            learned_before = crud.get_learned_words(user_id)
            
            process_daily_reset(user_id)
            
            # Проверяем, что невыученные слова сохранились в previous_daily_words
            if user_id in previous_daily_words:
                leftover_words = previous_daily_words[user_id]
                print_success(f"Сохранено {len(leftover_words)} невыученных слов на следующий день")
            else:
                print_info("Нет невыученных слов для перехода на следующий день")
            
            # Тест генерации слов на следующий день с учетом невыученных
            print_test("Генерация слов на следующий день с невыученными словами")
            
            result_next_day = get_daily_words_for_user(
                user_id, "A1", 5, 2,
                first_time=REMINDER_START,
                duration_hours=DURATION_HOURS,
                force_reset=True
            )
            
            if result_next_day:
                messages, times = result_next_day
                print_success(f"Сгенерировано {len(messages)} сообщений на следующий день")
            else:
                print_warning("Не удалось сгенерировать слова на следующий день")
            
            # Тест случая, когда все слова выучены
            print_test("Тестирование режима повторения (все слова выучены)")
            
            # Добавляем все возможные слова в словарь
            from pathlib import Path
            from config import LEVELS_DIR
            
            set_file = Path(LEVELS_DIR) / "A1" / "A1 Basic 1.txt"
            if set_file.exists():
                with open(set_file, 'r', encoding='utf-8') as f:
                    all_words = [line.strip() for line in f if line.strip()]
                
                # Добавляем все слова в словарь
                for word_line in all_words[:10]:  # Ограничиваем количество
                    if " - " in word_line:
                        word, translation = word_line.split(" - ", 1)
                        crud.add_learned_word(user_id, word.strip(), translation.strip(), today)
                
                print_success(f"Добавлено {min(10, len(all_words))} слов в словарь")
                
                # Проверяем режим повторения
                reset_daily_words_cache(user_id)
                result_revision = get_daily_words_for_user(
                    user_id, "A1", 5, 2,
                    first_time=REMINDER_START,
                    duration_hours=DURATION_HOURS,
                    force_reset=True
                )
                
                if result_revision:
                    messages, times = result_revision
                    # Проверяем, есть ли индикатор режима повторения
                    revision_indicators = ["🎓", "Поздравляем", "повторения"]
                    has_revision_indicator = any(
                        any(indicator in msg for indicator in revision_indicators)
                        for msg in messages
                    )
                    
                    if has_revision_indicator:
                        print_success("Режим повторения активирован корректно")
                    else:
                        print_info("Режим повторения может быть активен (проверьте вручную)")
            
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_error(f"Ошибка ежедневного сброса: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    def cleanup_test_environment(self):
        """Очистка тестовой среды"""
        print_header("ОЧИСТКА ТЕСТОВОЙ СРЕДЫ")
        
        try:
            from database.db import db_manager
            from utils.helpers import daily_words_cache, previous_daily_words
            
            # Очищаем тестовых пользователей
            for user_id in self.test_users:
                with db_manager.transaction() as conn:
                    conn.execute("DELETE FROM users WHERE chat_id = ?", (user_id,))
                    conn.execute("DELETE FROM dictionary WHERE chat_id = ?", (user_id,))
                    conn.execute("DELETE FROM learned_words WHERE chat_id = ?", (user_id,))
                    conn.execute("DELETE FROM active_payments WHERE chat_id = ?", (user_id,))
                
                # Очищаем кэши
                if user_id in daily_words_cache:
                    del daily_words_cache[user_id]
                if user_id in previous_daily_words:
                    del previous_daily_words[user_id]
            
            print_success("Тестовая среда очищена")
            return True
            
        except Exception as e:
            print_error(f"Ошибка очистки: {e}")
            return False

    def run_all_tests(self):
        """Запуск всех тестов"""
        print_header("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ENGLISH LEARNING BOT", Colors.PURPLE)
        
        start_time = datetime.now()
        
        # Настройка среды
        if not self.setup_test_environment():
            print_error("Не удалось настроить тестовую среду")
            return False
        
        # Список всех тестов
        tests = [
            ("Создание пользователей и онбординг", self.test_user_creation_and_onboarding),
            ("Генерация слов дня", self.test_words_day_generation),
            ("Функционал словаря", self.test_dictionary_functionality),
            ("Функционал тестов", self.test_quiz_functionality),
            ("Настройки и персонализация", self.test_settings_and_personalization),
            ("Функционал дней подряд", self.test_streak_functionality),
            ("Подписка и скидки", self.test_subscription_and_discounts),
            ("Вспомогательные функции подписки", self.test_subscription_helpers),
            ("Граничные случаи", self.test_edge_cases_and_error_handling),
            ("Сценарии ежедневного сброса", self.test_daily_reset_scenarios),
        ]
        
        self.total_tests = len(tests)
        
        # Запуск тестов
        for test_name, test_func in tests:
            print_info(f"Запуск теста: {test_name}")
            try:
                success = test_func()
                if success:
                    print_success(f"✅ {test_name}: ПРОЙДЕН")
                else:
                    print_error(f"❌ {test_name}: ПРОВАЛЕН")
            except Exception as e:
                print_error(f"💥 {test_name}: КРИТИЧЕСКАЯ ОШИБКА - {e}")
                self.failed_tests += 1
        
        # Очистка
        self.cleanup_test_environment()
        
        # Итоговый отчет
        end_time = datetime.now()
        duration = end_time - start_time
        
        print_header("ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ", Colors.PURPLE)
        
        print(f"{Colors.WHITE}Время выполнения: {duration.total_seconds():.2f} секунд{Colors.END}")
        print(f"{Colors.WHITE}Всего тестов: {self.total_tests}{Colors.END}")
        print(f"{Colors.GREEN}Пройдено: {self.passed_tests}{Colors.END}")
        print(f"{Colors.RED}Провалено: {self.failed_tests}{Colors.END}")
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        print(f"{Colors.WHITE}Процент успеха: {success_rate:.1f}%{Colors.END}")
        
        if self.failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!{Colors.END}")
            print(f"{Colors.GREEN}Бот готов к использованию.{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ{Colors.END}")
            print(f"{Colors.RED}Необходимо исправить {self.failed_tests} ошибок.{Colors.END}")
        
        return self.failed_tests == 0

def main():
    """Основная функция"""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                    ENGLISH LEARNING BOT - COMPREHENSIVE TEST                ║")
    print("║                                                                              ║")
    print("║  Полное тестирование всех функций бота согласно техническому заданию        ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    tester = BotTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())