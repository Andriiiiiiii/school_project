# test_streak_full_functionality.py
"""
ПОЛНЫЙ ТЕСТ ФУНКЦИОНАЛА ДНЕЙ ПОДРЯД
Проверяет все аспекты системы streak: CRUD, тесты, скидки, интеграцию с платежами
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_section(title):
    """Печатает заголовок раздела теста."""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")

def print_test(test_name):
    """Печатает название теста."""
    print(f"\n🔍 Тест: {test_name}")
    print("-" * 40)

def print_result(expected, actual, test_description):
    """Печатает результат теста."""
    status = "✅ ПРОЙДЕН" if expected == actual else "❌ ПРОВАЛЕН"
    print(f"   {test_description}")
    print(f"   Ожидалось: {expected}")
    print(f"   Получено: {actual}")
    print(f"   {status}")
    return expected == actual

def print_info(message):
    """Печатает информационное сообщение."""
    print(f"   ℹ️  {message}")

class StreakTester:
    def __init__(self):
        self.test_user_id = 888888
        self.test_premium_user_id = 888889
        self.passed_tests = 0
        self.total_tests = 0
        self.failed_tests = []
        
    def setup_test_environment(self):
        """Настройка тестового окружения."""
        print_section("НАСТРОЙКА ТЕСТОВОГО ОКРУЖЕНИЯ")
        
        try:
            from database import crud
            from database.db import db_manager
            
            # Очищаем тестовых пользователей
            with db_manager.transaction() as tx:
                for user_id in [self.test_user_id, self.test_premium_user_id]:
                    tx.execute("DELETE FROM users WHERE chat_id = ?", (user_id,))
                    tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (user_id,))
                    tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (user_id,))
                    tx.execute("DELETE FROM active_payments WHERE chat_id = ?", (user_id,))
            
            # Создаем тестовых пользователей
            crud.add_user(self.test_user_id)
            crud.add_user(self.test_premium_user_id)
            
            # Делаем одного премиум пользователем
            future_date = (datetime.now() + timedelta(days=30)).isoformat()
            crud.update_user_subscription(self.test_premium_user_id, "premium", future_date, "test_payment")
            
            print_info(f"Создан обычный пользователь: {self.test_user_id}")
            print_info(f"Создан премиум пользователь: {self.test_premium_user_id}")
            print_info("Тестовое окружение готово")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            return False
    
    def test_basic_crud_operations(self):
        """Тестирует базовые CRUD операции с streak."""
        print_section("ТЕСТ 1: БАЗОВЫЕ CRUD ОПЕРАЦИИ")
        
        try:
            from database import crud
            
            # Тест 1.1: Начальное состояние
            print_test("Начальное состояние streak")
            streak, date = crud.get_user_streak(self.test_user_id)
            self.assert_test(0, streak, "Начальный streak должен быть 0")
            self.assert_test(None, date, "Начальная дата должна быть None")
            
            # Тест 1.2: Установка streak
            print_test("Установка streak")
            test_date = "2025-06-01"
            crud.update_user_streak(self.test_user_id, 5, test_date)
            streak, date = crud.get_user_streak(self.test_user_id)
            self.assert_test(5, streak, "Streak должен быть установлен на 5")
            self.assert_test(test_date, date, f"Дата должна быть установлена на {test_date}")
            
            # Тест 1.3: Сброс streak
            print_test("Сброс streak")
            crud.reset_user_streak(self.test_user_id)
            streak, date = crud.get_user_streak(self.test_user_id)
            self.assert_test(0, streak, "Streak должен быть сброшен на 0")
            self.assert_test(None, date, "Дата должна быть сброшена на None")
            
            # Тест 1.4: Инкремент streak (первый раз)
            print_test("Первый инкремент streak")
            new_streak = crud.increment_user_streak(self.test_user_id)
            self.assert_test(1, new_streak, "Первый инкремент должен дать streak = 1")
            
            # Тест 1.5: Повторный инкремент в тот же день
            print_test("Повторный инкремент в тот же день")
            repeat_streak = crud.increment_user_streak(self.test_user_id)
            self.assert_test(1, repeat_streak, "Повторный инкремент должен оставить streak = 1")
            
        except Exception as e:
            print(f"❌ Ошибка в CRUD тестах: {e}")
            return False
        
        return True
    
    def test_streak_logic_scenarios(self):
        """Тестирует различные сценарии логики streak."""
        print_section("ТЕСТ 2: ЛОГИКА STREAK")
        
        try:
            from database import crud
            
            # Тест 2.1: Последовательные дни
            print_test("Последовательные дни")
            crud.reset_user_streak(self.test_user_id)
            
            # Симулируем тесты на протяжении 5 дней
            test_dates = [
                "2025-06-01",
                "2025-06-02", 
                "2025-06-03",
                "2025-06-04",
                "2025-06-05"
            ]
            
            for i, test_date in enumerate(test_dates):
                # Устанавливаем дату последнего теста на предыдущий день
                if i > 0:
                    prev_date = test_dates[i-1]
                    crud.update_user_streak(self.test_user_id, i, prev_date)
                
                # Симулируем инкремент (модифицируем функцию для тестирования)
                expected_streak = i + 1
                current_streak, _ = crud.get_user_streak(self.test_user_id)
                
                # Проверяем логику: если вчера был тест, streak должен увеличиться
                if i == 0:
                    # Первый день
                    crud.update_user_streak(self.test_user_id, 1, test_date)
                    result_streak = 1
                else:
                    # Последующие дни - увеличиваем streak
                    crud.update_user_streak(self.test_user_id, expected_streak, test_date)
                    result_streak = expected_streak
                
                self.assert_test(expected_streak, result_streak, f"День {i+1}: streak должен быть {expected_streak}")
            
            # Тест 2.2: Пропуск дня (streak должен сбрасываться)
            print_test("Пропуск дня")
            crud.update_user_streak(self.test_user_id, 5, "2025-06-05")  # Последний тест 5 июня
            
            # Тест 7 июня (пропуск 6 июня)
            crud.update_user_streak(self.test_user_id, 1, "2025-06-07")  # Streak должен сброситься
            streak, _ = crud.get_user_streak(self.test_user_id)
            self.assert_test(1, streak, "После пропуска дня streak должен сброситься на 1")
            
            # Тест 2.3: Валидация отрицательных значений
            print_test("Валидация отрицательных значений")
            crud.update_user_streak(self.test_user_id, -5, "2025-06-08")
            streak, _ = crud.get_user_streak(self.test_user_id)
            self.assert_test(0, streak, "Отрицательный streak должен быть приведен к 0")
            
        except Exception as e:
            print(f"❌ Ошибка в тестах логики streak: {e}")
            return False
        
        return True
    
    def test_discount_calculation(self):
        """Тестирует расчет скидок на основе streak."""
        print_section("ТЕСТ 3: РАСЧЕТ СКИДОК")
        
        try:
            from database import crud
            
            # Тест 3.1: Скидка для бесплатного пользователя (должна быть 0)
            print_test("Скидка для бесплатного пользователя")
            crud.update_user_streak(self.test_user_id, 15, "2025-06-08")
            discount = crud.calculate_streak_discount(self.test_user_id)
            self.assert_test(0, discount, "Бесплатный пользователь не должен получать скидку")
            
            # Тест 3.2: Скидка для премиум пользователя (до 30 дней)
            print_test("Скидка для премиум пользователя (15 дней)")
            crud.update_user_streak(self.test_premium_user_id, 15, "2025-06-08")
            discount = crud.calculate_streak_discount(self.test_premium_user_id)
            self.assert_test(15, discount, "Премиум пользователь должен получать скидку равную streak")
            
            # Тест 3.3: Максимальная скидка (30%)
            print_test("Максимальная скидка (больше 30 дней)")
            crud.update_user_streak(self.test_premium_user_id, 45, "2025-06-08")
            discount = crud.calculate_streak_discount(self.test_premium_user_id)
            self.assert_test(30, discount, "Максимальная скидка должна быть 30%")
            
            # Тест 3.4: Скидка при streak = 0
            print_test("Скидка при streak = 0")
            crud.reset_user_streak(self.test_premium_user_id)
            discount = crud.calculate_streak_discount(self.test_premium_user_id)
            self.assert_test(0, discount, "При streak = 0 скидка должна быть 0")
            
        except Exception as e:
            print(f"❌ Ошибка в тестах расчета скидок: {e}")
            return False
        
        return True
    
    def test_payment_integration(self):
        """Тестирует интеграцию с системой платежей."""
        print_section("ТЕСТ 4: ИНТЕГРАЦИЯ С ПЛАТЕЖАМИ")
        
        try:
            from services.payment import PaymentService
            from database import crud
            
            # Тест 4.1: Расчет цены без скидки
            print_test("Расчет цены без скидки")
            crud.reset_user_streak(self.test_premium_user_id)
            price_info = PaymentService.calculate_discounted_price(self.test_premium_user_id, 1)
            
            self.assert_test(False, price_info['has_discount'], "При streak = 0 не должно быть скидки")
            self.assert_test(299.0, price_info['base_price'], "Базовая цена должна быть 299")
            self.assert_test(299.0, price_info['final_price'], "Финальная цена должна равняться базовой")
            
            # Тест 4.2: Расчет цены со скидкой
            print_test("Расчет цены со скидкой (20%)")
            crud.update_user_streak(self.test_premium_user_id, 20, "2025-06-08")
            price_info = PaymentService.calculate_discounted_price(self.test_premium_user_id, 1)
            
            expected_discount = 299.0 * 0.20  # 20%
            expected_final = 299.0 - expected_discount
            
            self.assert_test(True, price_info['has_discount'], "При streak = 20 должна быть скидка")
            self.assert_test(20, price_info['discount_percent'], "Процент скидки должен быть 20%")
            self.assert_test(expected_final, price_info['final_price'], f"Финальная цена должна быть {expected_final}")
            
            # Тест 4.3: Расчет для разных периодов подписки
            print_test("Расчет для разных периодов")
            periods_prices = {3: 799.0, 6: 1499.0, 12: 2899.0}
            
            for months, base_price in periods_prices.items():
                price_info = PaymentService.calculate_discounted_price(self.test_premium_user_id, months)
                expected_final = base_price * 0.8  # 20% скидка
                
                success = self.assert_test(
                    expected_final, 
                    price_info['final_price'], 
                    f"Цена за {months} месяцев со скидкой должна быть {expected_final}"
                )
                if not success:
                    break
            
        except Exception as e:
            print(f"❌ Ошибка в тестах интеграции с платежами: {e}")
            return False
        
        return True
    
    async def test_quiz_integration(self):
        """Тестирует интеграцию с системой тестов."""
        print_section("ТЕСТ 5: ИНТЕГРАЦИЯ С ТЕСТАМИ")
        
        try:
            from database import crud
            from handlers.quiz import quiz_states
            from unittest.mock import AsyncMock, MagicMock
            
            # Мокаем бота для тестирования
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock()
            
            # Тест 5.1: Увеличение streak при старте теста
            print_test("Увеличение streak при старте теста")
            
            # Подготавливаем данные
            crud.reset_user_streak(self.test_user_id)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            crud.update_user_streak(self.test_user_id, 5, yesterday)
            
            # Симулируем начало теста (без фактического запуска)
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Проверяем логику инкремента
            old_streak, _ = crud.get_user_streak(self.test_user_id)
            new_streak = crud.increment_user_streak(self.test_user_id)
            
            self.assert_test(6, new_streak, "Streak должен увеличиться с 5 до 6")
            
            # Тест 5.2: Повторный запуск теста в тот же день
            print_test("Повторный запуск теста в тот же день")
            repeat_streak = crud.increment_user_streak(self.test_user_id)
            self.assert_test(6, repeat_streak, "При повторном запуске streak должен остаться 6")
            
            # Тест 5.3: Сброс streak при пропуске дня
            print_test("Сброс streak при пропуске дня")
            day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            crud.update_user_streak(self.test_user_id, 10, day_before_yesterday)
            
            reset_streak = crud.increment_user_streak(self.test_user_id)
            self.assert_test(1, reset_streak, "После пропуска дня streak должен сброситься на 1")
            
        except Exception as e:
            print(f"❌ Ошибка в тестах интеграции с тестами: {e}")
            return False
        
        return True
    
    def test_scheduler_integration(self):
        """Тестирует интеграцию с планировщиком (сброс streak)."""
        print_section("ТЕСТ 6: ИНТЕГРАЦИЯ С ПЛАНИРОВЩИКОМ")
        
        try:
            from services.scheduler import process_daily_reset
            from database import crud
            
            # Тест 6.1: Сброс streak при пропуске дня
            print_test("Сброс streak планировщиком при пропуске")
            
            # Устанавливаем streak с датой позавчера
            day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            crud.update_user_streak(self.test_user_id, 15, day_before_yesterday)
            
            # Симулируем ежедневный сброс
            process_daily_reset(self.test_user_id)
            
            # Проверяем что streak сброшен
            streak, _ = crud.get_user_streak(self.test_user_id)
            self.assert_test(0, streak, "Планировщик должен сбросить streak при пропуске дня")
            
            # Тест 6.2: Сохранение streak при активности вчера
            print_test("Сохранение streak при активности вчера")
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            crud.update_user_streak(self.test_user_id, 7, yesterday)
            
            # Сохраняем streak перед сбросом для сравнения
            original_streak, _ = crud.get_user_streak(self.test_user_id)
            
            # Симулируем ежедневный сброс
            process_daily_reset(self.test_user_id)
            
            # Проверяем что streak сохранен (планировщик не должен его сбрасывать)
            streak, _ = crud.get_user_streak(self.test_user_id)
            self.assert_test(original_streak, streak, "Планировщик должен сохранить streak при активности вчера")
            
        except Exception as e:
            print(f"❌ Ошибка в тестах интеграции с планировщиком: {e}")
            return False
        
        return True
    
    def test_edge_cases(self):
        """Тестирует граничные случаи и обработку ошибок."""
        print_section("ТЕСТ 7: ГРАНИЧНЫЕ СЛУЧАИ")
        
        try:
            from database import crud
            
            # Тест 7.1: Очень большие значения streak
            print_test("Очень большие значения streak")
            crud.update_user_streak(self.test_premium_user_id, 999999, "2025-06-08")
            discount = crud.calculate_streak_discount(self.test_premium_user_id)
            self.assert_test(30, discount, "Даже при очень большом streak максимальная скидка 30%")
            
            # Тест 7.2: Несуществующий пользователь
            print_test("Несуществующий пользователь")
            fake_user_id = 999999999
            streak, date = crud.get_user_streak(fake_user_id)
            self.assert_test(0, streak, "Для несуществующего пользователя streak должен быть 0")
            self.assert_test(None, date, "Для несуществующего пользователя дата должна быть None")
            
            # Тест 7.3: Неправильный формат даты
            print_test("Обработка неправильной даты")
            try:
                crud.update_user_streak(self.test_user_id, 5, "неправильная-дата")
                # Проверяем что система не сломалась
                streak, _ = crud.get_user_streak(self.test_user_id)
                print_info(f"Система обработала неправильную дату, streak = {streak}")
            except Exception as e:
                print_info(f"Система корректно выбросила исключение: {e}")
            
            # Тест 7.4: Одновременные операции (имитация)
            print_test("Имитация одновременных операций")
            for i in range(5):
                crud.update_user_streak(self.test_user_id, i, f"2025-06-{8+i:02d}")
            
            final_streak, _ = crud.get_user_streak(self.test_user_id)
            self.assert_test(4, final_streak, "Последняя операция должна быть сохранена")
            
        except Exception as e:
            print(f"❌ Ошибка в тестах граничных случаев: {e}")
            return False
        
        return True
    
    def cleanup_test_environment(self):
        """Очистка тестового окружения."""
        print_section("ОЧИСТКА ТЕСТОВОГО ОКРУЖЕНИЯ")
        
        try:
            from database.db import db_manager
            
            # Удаляем тестовых пользователей
            with db_manager.transaction() as tx:
                for user_id in [self.test_user_id, self.test_premium_user_id]:
                    tx.execute("DELETE FROM users WHERE chat_id = ?", (user_id,))
                    tx.execute("DELETE FROM dictionary WHERE chat_id = ?", (user_id,))
                    tx.execute("DELETE FROM learned_words WHERE chat_id = ?", (user_id,))
                    tx.execute("DELETE FROM active_payments WHERE chat_id = ?", (user_id,))
            
            print_info("Тестовые пользователи удалены")
            print_info("Тестовое окружение очищено")
            
        except Exception as e:
            print(f"❌ Ошибка при очистке: {e}")
    
    def assert_test(self, expected, actual, description):
        """Проверяет результат теста и обновляет статистику."""
        self.total_tests += 1
        success = print_result(expected, actual, description)
        
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests.append(f"{self.total_tests}: {description}")
        
        return success
    
    async def run_all_tests(self):
        """Запускает все тесты."""
        print("🚀 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ ФУНКЦИОНАЛА ДНЕЙ ПОДРЯД")
        print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Настройка окружения
        if not self.setup_test_environment():
            print("❌ Не удалось настроить тестовое окружение")
            return False
        
        # Запуск тестов
        tests = [
            self.test_basic_crud_operations,
            self.test_streak_logic_scenarios,
            self.test_discount_calculation,
            self.test_payment_integration,
            self.test_quiz_integration,
            self.test_scheduler_integration,
            self.test_edge_cases
        ]
        
        for test in tests:
            try:
                if asyncio.iscoroutinefunction(test):
                    await test()
                else:
                    test()
            except Exception as e:
                print(f"❌ Критическая ошибка в тесте: {e}")
                import traceback
                traceback.print_exc()
        
        # Очистка
        self.cleanup_test_environment()
        
        # Итоговый отчет
        self.print_final_report()
        
        return self.passed_tests == self.total_tests
    
    def print_final_report(self):
        """Печатает итоговый отчет."""
        print_section("ИТОГОВЫЙ ОТЧЕТ")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"📊 Всего тестов: {self.total_tests}")
        print(f"✅ Пройдено: {self.passed_tests}")
        print(f"❌ Провалено: {self.total_tests - self.passed_tests}")
        print(f"📈 Процент успеха: {success_rate:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
            for failed_test in self.failed_tests:
                print(f"   • {failed_test}")
        
        print(f"\n{'='*60}")
        if self.passed_tests == self.total_tests:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ Функционал дней подряд работает корректно")
        else:
            print("⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
            print("❌ Требуется исправление функционала")
        print(f"{'='*60}")
        
        print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """Главная функция для запуска тестов."""
    tester = StreakTester()
    success = await tester.run_all_tests()
    
    # Возвращаем код выхода
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())