# manual_streak_test.py
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def interactive_streak_test():
    """Интерактивное тестирование streak функционала."""
    print("🎮 ИНТЕРАКТИВНОЕ ТЕСТИРОВАНИЕ STREAK ФУНКЦИОНАЛА")
    print("=" * 60)
    
    try:
        from database import crud
        from services.payment import PaymentService
        
        # Получаем chat_id пользователя
        while True:
            try:
                chat_id = int(input("Введите ваш chat_id (или 999999 для тестового): "))
                break
            except ValueError:
                print("❌ Пожалуйста, введите корректный chat_id (число)")
        
        # Проверяем/создаем пользователя
        user = crud.get_user(chat_id)
        if not user:
            print(f"👤 Пользователь {chat_id} не найден. Создаю...")
            crud.add_user(chat_id)
            print("✅ Пользователь создан")
        else:
            print(f"👤 Пользователь {chat_id} найден")
        
        while True:
            print("\n" + "=" * 50)
            print("МЕНЮ ТЕСТИРОВАНИЯ:")
            print("1. Показать текущий streak")
            print("2. Увеличить streak (симуляция прохождения теста)")
            print("3. Установить конкретный streak")
            print("4. Сбросить streak")
            print("5. Показать расчет скидки")
            print("6. Сделать пользователя премиум")
            print("7. Убрать премиум статус")
            print("8. Симулировать пропуск дня")
            print("9. Показать цены со скидкой")
            print("0. Выход")
            
            choice = input("\nВыберите действие (0-9): ").strip()
            
            if choice == "0":
                print("👋 До свидания!")
                break
            elif choice == "1":
                streak, last_date = crud.get_user_streak(chat_id)
                print(f"\n📊 Текущий streak: {streak} дней")
                print(f"📅 Последний тест: {last_date or 'никогда'}")
                
            elif choice == "2":
                old_streak, _ = crud.get_user_streak(chat_id)
                new_streak = crud.increment_user_streak(chat_id)
                print(f"\n🚀 Streak увеличен: {old_streak} → {new_streak}")
                
            elif choice == "3":
                try:
                    new_streak = int(input("Введите новое значение streak: "))
                    today = datetime.now().strftime("%Y-%m-%d")
                    crud.update_user_streak(chat_id, new_streak, today)
                    print(f"✅ Streak установлен: {new_streak}")
                except ValueError:
                    print("❌ Введите корректное число")
                    
            elif choice == "4":
                crud.reset_user_streak(chat_id)
                print("🔄 Streak сброшен до 0")
                
            elif choice == "5":
                discount = crud.calculate_streak_discount(chat_id)
                streak, _ = crud.get_user_streak(chat_id)
                is_premium = crud.is_user_premium(chat_id)
                
                print(f"\n💰 РАСЧЕТ СКИДКИ:")
                print(f"   Streak: {streak} дней")
                print(f"   Премиум: {'Да' if is_premium else 'Нет'}")
                print(f"   Скидка: {discount}%")
                
                if not is_premium:
                    print("   💡 Скидка доступна только премиум пользователям")
                    
            elif choice == "6":
                future_date = (datetime.now() + timedelta(days=30)).isoformat()
                crud.update_user_subscription(chat_id, "premium", future_date, "manual_test")
                print("💎 Пользователь теперь премиум (30 дней)")
                
            elif choice == "7":
                crud.update_user_subscription(chat_id, "free")
                print("🆓 Премиум статус убран")
                
            elif choice == "8":
                print("\n🕐 Симуляция пропуска дня...")
                yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
                old_streak, _ = crud.get_user_streak(chat_id)
                crud.update_user_streak(chat_id, old_streak, yesterday)
                
                # Симулируем ежедневный сброс
                from services.scheduler import process_daily_reset
                process_daily_reset(chat_id)
                
                new_streak, _ = crud.get_user_streak(chat_id)
                print(f"   Streak до пропуска: {old_streak}")
                print(f"   Streak после пропуска: {new_streak}")
                
            elif choice == "9":
                is_premium = crud.is_user_premium(chat_id)
                if not is_premium:
                    print("❌ Пользователь не премиум. Скидки недоступны.")
                else:
                    print(f"\n💸 ЦЕНЫ СО СКИДКОЙ:")
                    for months in [1, 3, 6, 12]:
                        price_info = PaymentService.calculate_discounted_price(chat_id, months)
                        period = {1: "1 мес", 3: "3 мес", 6: "6 мес", 12: "1 год"}[months]
                        
                        print(f"\n   {period}:")
                        print(f"     Базовая цена: {price_info['base_price']:.0f}₽")
                        if price_info['has_discount']:
                            print(f"     Скидка ({price_info['discount_percent']}%): -{price_info['discount_amount']:.0f}₽")
                            print(f"     К оплате: {price_info['final_price']:.0f}₽")
                        else:
                            print(f"     К оплате: {price_info['final_price']:.0f}₽ (без скидки)")
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
        
    except KeyboardInterrupt:
        print("\n\n👋 Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    interactive_streak_test()