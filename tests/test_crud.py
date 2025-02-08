# tests/test_crud.py
import unittest
from database import crud
from database.db import conn, cursor

class TestCRUD(unittest.TestCase):
    test_chat_id = 999999  # Используем уникальный идентификатор для тестирования

    def setUp(self):
        # Перед каждым тестом удаляем пользователя с тестовым chat_id (если существует)
        cursor.execute("DELETE FROM users WHERE chat_id = ?", (self.test_chat_id,))
        cursor.execute("DELETE FROM dictionary WHERE chat_id = ?", (self.test_chat_id,))
        conn.commit()

    def tearDown(self):
        # После каждого теста очищаем записи, связанные с тестовым пользователем
        cursor.execute("DELETE FROM users WHERE chat_id = ?", (self.test_chat_id,))
        cursor.execute("DELETE FROM dictionary WHERE chat_id = ?", (self.test_chat_id,))
        conn.commit()

    def test_add_and_get_user(self):
        """Проверяем, что функция add_user корректно добавляет пользователя, а get_user – его возвращает."""
        crud.add_user(self.test_chat_id)
        user = crud.get_user(self.test_chat_id)
        self.assertIsNotNone(user, "Пользователь должен быть добавлен в базу")
        # Предполагаем, что структура user: (chat_id, level, words_per_day, notifications, reminder_time)
        self.assertEqual(user[0], self.test_chat_id)
        self.assertEqual(user[1], 'A1')     # уровень по умолчанию
        self.assertEqual(user[2], 5)        # количество слов по умолчанию
        self.assertEqual(user[3], 10)       # количество уведомлений по умолчанию
        self.assertEqual(user[4], '09:00')  # время напоминания по умолчанию

    def test_update_user_level(self):
        """Проверяем, что функция update_user_level обновляет уровень пользователя."""
        crud.add_user(self.test_chat_id)
        crud.update_user_level(self.test_chat_id, 'B2')
        user = crud.get_user(self.test_chat_id)
        self.assertEqual(user[1], 'B2', "Уровень должен быть обновлен на B2")

    def test_update_user_words_per_day(self):
        """Проверяем, что функция update_user_words_per_day обновляет число слов в день."""
        crud.add_user(self.test_chat_id)
        crud.update_user_words_per_day(self.test_chat_id, 7)
        user = crud.get_user(self.test_chat_id)
        self.assertEqual(user[2], 7, "Количество слов должно быть обновлено на 7")

    def test_update_user_notifications(self):
        """Проверяем, что функция update_user_notifications обновляет число уведомлений."""
        crud.add_user(self.test_chat_id)
        crud.update_user_notifications(self.test_chat_id, 15)
        user = crud.get_user(self.test_chat_id)
        self.assertEqual(user[3], 15, "Количество уведомлений должно быть обновлено на 15")

    def test_update_user_reminder_time(self):
        """Проверяем, что функция update_user_reminder_time обновляет время напоминания."""
        crud.add_user(self.test_chat_id)
        crud.update_user_reminder_time(self.test_chat_id, "12:30")
        user = crud.get_user(self.test_chat_id)
        self.assertEqual(user[4], "12:30", "Время напоминания должно быть обновлено на 12:30")

    def test_add_word_to_dictionary_and_get(self):
        """Проверяем, что слово добавляется в словарь и его можно извлечь."""
        crud.add_user(self.test_chat_id)
        word_data = {
            "word": "apple",
            "translation": "яблоко",
            "transcription": "/ˈæp.əl/",
            "example": "I ate an apple."
        }
        crud.add_word_to_dictionary(self.test_chat_id, word_data)
        dictionary = crud.get_user_dictionary(self.test_chat_id, limit=10, offset=0)
        # Проверяем, что словарь не пуст и содержит слово "apple"
        self.assertGreaterEqual(len(dictionary), 1, "Словарь должен содержать хотя бы одну запись")
        found = any(entry[0] == "apple" for entry in dictionary)
        self.assertTrue(found, "Слово 'apple' должно присутствовать в словаре")

if __name__ == '__main__':
    unittest.main()
