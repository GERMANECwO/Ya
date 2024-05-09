import telebot
from info import *
from iam import *
import requests
import sqlite3
import os
import time
import json
from datetime import datetime
import logging


bot = telebot.TeleBot(TOKEN)




MAX_USERS = 5
MAX_SYMBOLS_FOR_USER = 600
MAX_TOKENS_FOR_USER = 600
MAX_SOUNDS_FOR_SST_FOR_USER = 13
MAX_TOKENS = 60

def count_symb(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    sql_query = "UPDATE users_data SET task_for_tts = ? WHERE user_id = ?;"
    cur.execute(sql_query, (message.text, user_id))
    connection.commit()
    user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
    task_for_tts = user_data[6]
    if message.content_type != "text":
        print(message.content_type)
        bot.send_message(message.chat.id, text="Пришлите текст!")
    elif len(task_for_tts) > 15:
        bot.send_message(message.chat.id, text="Слишком длинный текст")
        logging.info(f"Пользователь с id - {user_id} отправил слишком длинное текстовое сообщение")

    else:
        logging.info(f"Пользователь с id - {user_id} обратился к SpeechKit для tts")
            # Аутентификация через IAM-токен
        headers = {
            'Authorization': f'Bearer {get_creds()}',
        }
        data = {
            'text': task_for_tts,  # текст, который нужно преобразовать в голосовое сообщение
            'lang': 'ru-RU',  # язык текста - русский
            'voice': 'ermil',  # голос 
            'folderId': folder_id,
        }
        # Выполняем запрос
        response = requests.post('https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize', headers=headers, data=data)

        if response.status_code == 200:
            with open(f"output{user_id}.ogg", "wb") as audio_file:
                audio_file.write(response.content)
            logging.info(f"Аудиофайл успешно сохранен как output{user_id}.ogg")
            
            audio = open(f"output{user_id}.ogg", 'rb')
            bot.send_audio(message.chat.id, audio)
            audio.close()
            os.remove (f"output{user_id}.ogg")

            logging.info(f"Аудиофайл успешно удалён как output{user_id}.ogg")

            user_symbols_for_tts = cur.execute(f'''SELECT symbols_for_tts FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
            print(user_symbols_for_tts)
            user_symbols_for_tts_2 = user_symbols_for_tts + len(task_for_tts)
            print(user_symbols_for_tts_2)
            sql_query = "UPDATE users_data SET symbols_for_tts = ? WHERE user_id = ?;"
            cur.execute(sql_query, (user_symbols_for_tts_2, user_id))
            connection.commit()
            
        else:
            logging.warning("При запросе в SpeechKit возникла ошибка")
    connection.close()

def count_sec(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    if message.content_type != "voice":
        print(message.content_type)
        bot.send_message(message.chat.id, text="Пришлите голосовое сообщение!")
    elif message.voice.duration > 15:
        bot.send_message(message.chat.id, text="Слишком длинное сообщение")
        logging.info(f"Пользователь с id - {user_id} отправил слишком длинное голосовое сообщение")
    else:
        logging.info(f"Пользователь с id - {user_id} обратился к SpeechKit для stt")
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        sounds_for_sst_sec = cur.execute(f'''SELECT sounds_for_sst FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
        sounds_for_sst_sec = sounds_for_sst_sec + message.voice.duration
        sql_query = "UPDATE users_data SET sounds_for_sst = ? WHERE user_id = ?;"
        cur.execute(sql_query, (sounds_for_sst_sec, user_id))
        connection.commit()
        def speech_to_text(data):
            # Указываем параметры запроса
            params = "&".join([
            "topic=general",  # используем основную версию модели
            f"folderId={folder_id}",
            "lang=ru-RU"  # распознаём голосовое сообщение на русском языке
            ])

            # Аутентификация через IAM-токен
            headers = {
                'Authorization': f'Bearer {get_creds()}',
            }
                
                # Выполняем запрос
            response = requests.post(
                    f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}",
                headers=headers, 
                data=data
            )
            # Читаем json в словарь
            decoded_data = response.json()
            # Проверяем, не произошла ли ошибка при запросе
            if decoded_data.get("error_code") is None:
                logging.info(decoded_data.get("result"))
                return True, decoded_data.get("result")  # Возвращаем статус и текст из аудио
            else:
                logging.warning("При запросе в SpeechKit возникла ошибка")
                return False
            

        success, result = speech_to_text(file)

        # Проверяем успешность распознавания и выводим результат
        if success:
            bot.send_message(message.chat.id, text=f"Распознанный текст:\n{result}")
        else:
            bot.send_message(message.chat.id, text=f"Ошибка при распознавании речи:\n{result}")
            logging.warning(f"При запросе в SpeechKit возникла ошибка при распознавании речи:\n{result}")
