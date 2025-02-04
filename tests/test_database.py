# tests/test_database.py
import unittest
from database import crud

class TestDatabase(unittest.TestCase):
    def test_add_and_get_user(self):
        chat_id = 123456
        crud.add_user(chat_id)
        user = crud.get_user(chat_id)
        self.assertIsNotNone(user)
        self.assertEqual(user[0], chat_id)

if __name__ == '__main__':
    unittest.main()
