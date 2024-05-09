
from kit_speach import *
from gpt import *
import sqlite3
import logging

bot = telebot.TeleBot(TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
    encoding='utf-8',
)

MAX_USERS = 5
MAX_SYMBOLS_FOR_USER = 600
MAX_TOKENS_FOR_USER = 600
MAX_SOUNDS_FOR_SST_FOR_USER = 13
MAX_TOKENS = 60


def create_db():
    logging.info("Создана БД")
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    sql_query = ('CREATE TABLE IF NOT EXISTS users_data (' 
                 'id INTEGER PRIMARY KEY, ' 
                 'user_id INTEGER,' 
                 'user_name TEXT, ' 
                 'user_role TEXT, ' 
                 'tokens INTEGER, ' 
                 'symbols_for_tts INTEGER, ' 
                 'task_for_tts INTEGER, ' 
                 'sounds_for_sst INTEGER, ' 
                 'task TEXT)'
                 )
    cur.execute(sql_query)
    connection.close()


def exist_user(user_id):
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    query = f'''SELECT user_id FROM users_data WHERE user_id = {user_id}'''
    results = cur.execute(query)
    try:
        results = results.fetchone()[0]
    except:
        results = None
    connection.close()
    return results == user_id


def is_limit_users():
    global MAX_USERS
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    result = cursor.execute('SELECT DISTINCT user_id FROM users_data;')
    count = 0
    for i in result:
        count += 1
    connection.close()
    return count >= MAX_USERS


@bot.message_handler(commands=["start"])
def welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    logging.info(f"Пользователь с id - {user_id} использовал комманду /start")
    if not exist_user(user_id):
        # Если пользователя нет, добавляем его в базу данных
        sql_query = "INSERT INTO users_data (user_id, user_name, user_role, tokens, symbols_for_tts, task_for_tts, sounds_for_sst, task) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        cur.execute(sql_query, (
        user_id, user_name, "user", MAX_TOKENS, MAX_SYMBOLS_FOR_USER, MAX_TOKENS_FOR_USER, MAX_SOUNDS_FOR_SST_FOR_USER,
        " "))
        connection.commit()
        logging.info(f"Новый пользователь с id - {user_id} добавлен в базу данных")
        bot.send_message(message.chat.id,
                         "Приветствую, пользователь!\nДля работы с GPT пришлите промт в виде текста или голосового сообщения!")
    else:
        logging.info(f"Отправлено приветственное сообщение пользователю с id - {user_id}")
        bot.send_message(message.chat.id,
                         "Приветствую, пользователь!\nДля работы с GPT пришлите промт в виде текста или голосового сообщения!")
        sql_query = "UPDATE users_data SET task = ? WHERE user_id = ?;"
        cur.execute(sql_query, (" ", user_id))
        connection.commit()

    connection.close()


@bot.message_handler(commands=["tts"])
def tts_func(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    logging.info(f"Пользователь с id - {user_id} использовал комманду /tts")
    user_symbols_for_tts = 0
    try:
        user_symbols_for_tts = count_symb()
        cur.execute(f'''SELECT symbols_for_tts FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
    except:
        logging.warning(f"Пользователю с id - {user_id} не удалость получить его символы для tts")
    if exist_user(user_id):
        if not is_limit_users():
            if user_symbols_for_tts > MAX_SYMBOLS_FOR_USER:
                bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во символов")
                logging.info(f"У пользователя с id - {user_id} закончилость доступное кол-во символов для tts")

            else:
                sql_query = "UPDATE users_data SET task_for_tts = ? WHERE user_id = ?;"
                cur.execute(sql_query, (" ", user_id))
                connection.commit()
                bot.send_message(message.chat.id, "Напиши текст для озвучки")
                bot.register_next_step_handler(message, count_symb)
        else:
            logging.warning("Бот пререгружен")
            bot.send_message(message.chat.id, text="Извиняемся, но в данный момент бот перегружен!")

    else:
        logging.info(f"Пользователь с id - {user_id} отказано в доступе")
        bot.send_message(message.chat.id, text="У вас нет доступа к использованию бота!")
    connection.close()


@bot.message_handler(commands=["stt"])
def stt_func(message):
    user_id = message.from_user.id
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    logging.info(f"Пользователь с id - {user_id} использовал комманду /stt")
    try:
        user_sounds_for_sst = \
            cur.execute(f'''SELECT sounds_for_sst FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
    except:
        logging.warning(f"Пользователю с id - {user_id} не удалость получить его аудио блоки для stt")

    if exist_user(user_id):
        if is_limit_users() == False:
            if user_sounds_for_sst > MAX_SOUNDS_FOR_SST_FOR_USER:
                bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во звуковых сообщений")

            else:
                bot.send_message(message.chat.id, "Пришли голосовое сообщение (не более 15-ти секунд!)")
                bot.register_next_step_handler(message, count_sec)
        else:
            bot.send_message(message.chat.id, text="Извиняемся, но в данный момент бот перегружен!")
            logging.warning("Бот пререгружен")
    else:
        bot.send_message(message.chat.id, text="У вас нет доступа к использованию бота!")
        logging.info(f"Пользователь с id - {user_id} отказано в доступе")
    connection.close()


@bot.message_handler(commands=["logs"])
def stt_func(message):
    user_id = message.from_user.id
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    logging.info(f"Пользователь с id - {user_id} использовал комманду /logs")
    try:
        user_role = cur.execute(f'''SELECT user_role FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
    except:
        logging.warning(f"Пользователю с id - {user_id} не удалость получить его должность")

    if exist_user(user_id):
        if not is_limit_users():
            doc = open('log_file.txt', 'rb')
            bot.send_document(message.chat.id, doc)
            logging.warning(f"Пользователю с id - {user_id} отправлен файл с логами")
        else:
            bot.send_message(message.chat.id, text="Извиняемся, но в данный момент бот перегружен!")
            logging.warning("Бот пререгружен")
    else:
        bot.send_message(message.chat.id, text="У вас нет доступа к использованию бота!")

        logging.info(f"Пользователь с id - {user_id} отказано в доступе")
    connection.close()


@bot.message_handler(content_types=["text"])
def send_text(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    logging.info(f"Пользователь с id - {user_id} отправил текстовое сообщение - {message.text}")
    if not exist_user(user_id):
        if not is_limit_users():
            try:
                connection = sqlite3.connect('database.db')
                cur = connection.cursor()
                sql = "INSERT INTO users_data (user_id, user_name, user_role, tokens, symbols_for_tts, task_for_tts, sounds_for_sst, task) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
                data = (user_id, user_name, "User", 0, 0, " ", 0, " ")
                cur.execute(sql, data)
                connection.commit()
                bot.send_message(message.chat.id, text="Доступ к боту разрешён")
                logging.info(f"Пользователь с id - {user_id} зарегистрировался в боте")
            except sqlite3.Error as error:
                logging.warning("Ошибка при работе с SQLite", error)
        else:
            bot.send_message(message.chat.id, text="Извиняемся, но в данный момент бот перегружен!")
            logging.warning("Бот пререгружен")
        return
    if message.content_type == "text":
        logging.info(
            f"Пользователь с id - {user_id} отправил текстовое сообщение - '{message.text}' и обратился с ним к GPT")
        count_tokens(message)
    connection.close()


@bot.message_handler(content_types=["voice"])
def send_text(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    if not exist_user(user_id):
        bot.send_message(message.chat.id, text="У вас нет доступа к использованию бота!")
        logging.info(f"Пользователь с id - {user_id} отказано в доступе")
    if message.content_type == "voice" and exist_user(user_id):
        logging.info(f"Пользователь с id - {user_id} отправил голосовое сообщение - и обратился с ним к GPT")
        voice_gpt(message)


create_db()
bot.polling()
