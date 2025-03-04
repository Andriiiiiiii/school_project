# clear_user_cache.py
from utils.helpers import daily_words_cache

def clear_user_cache(chat_id):
    if chat_id in daily_words_cache:
        del daily_words_cache[chat_id]
        print(f"Кэш для пользователя {chat_id} очищен.")
    else:
        print(f"Для пользователя {chat_id} кэш не найден.")

if __name__ == '__main__':
    my_chat_id = 1999873173   # замените на нужный chat_id
    clear_user_cache(my_chat_id)
