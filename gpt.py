import telebot
from info import *
from iam import *
import requests
import sqlite3

import logging

bot = telebot.TeleBot(TOKEN)

MAX_USERS = 5
MAX_SYMBOLS_FOR_USER = 600
MAX_TOKENS_FOR_USER = 600
MAX_SOUNDS_FOR_SST_FOR_USER = 13
MAX_TOKENS = 60


def count_tokens(message):
    user_id = message.from_user.id
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()

    user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
    task = user_data[8]

    sql_query = "UPDATE users_data SET task = ? WHERE user_id = ?;"
    cur.execute(sql_query, (f"{task}\n'user': {message.text}", user_id))
    connection.commit()

    user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
    task_2 = user_data[8]

    print(task)
    print(task_2)

    token = get_creds()
    headers = {  # заголовок запроса, в котором передаем IAM-токен
        'Authorization': f'Bearer {token}',  # token - наш IAM-токен
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",  # указываем folder_id
        "maxTokens": MAX_TOKENS,
        "text": task
    }
    tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
    int(str(tokens))
    new_tokens = tokens + len(requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize", json=data,
                                            headers=headers).json()['tokens'])

    sql_query = "UPDATE users_data SET tokens = ? WHERE user_id = ?;"
    cur.execute(sql_query, (new_tokens, user_id))
    connection.commit()
    tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]

    if tokens > MAX_TOKENS_FOR_USER:
        logging.info(f"У пользователя с id - {user_id} закончилость доступное кол-во токенов")
        bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во токенов!")
    else:
        ask_gpt(message)


def ask_gpt(message):
    user_id = message.from_user.id
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()

    user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
    task = user_data[8]

    print(task)

    headers = {
        'Authorization': f'Bearer {get_creds()}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": MAX_TOKENS
        },
        "messages": [
            {
                "role": "user",
                "text": task
            }
        ]
    }

    # Выполняем запрос к YandexGPT
    response = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                             headers=headers,
                             json=data)

    # Проверяем, не произошла ли ошибка при запросе
    if response.status_code == 200:
        user_id = message.from_user.id
        connection = sqlite3.connect('database.db')
        cur = connection.cursor()
        text = response.json()["result"]["alternatives"][0]["message"]["text"]

        tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
        new_tokens = tokens + MAX_TOKENS
        sql_query = "UPDATE users_data SET tokens = ? WHERE user_id = ?;"
        cur.execute(sql_query, (new_tokens, user_id))

        user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
        task = user_data[8]

        sql_query = "UPDATE users_data SET task = ? WHERE user_id = ?;"
        cur.execute(sql_query, (f"{task}'\n''assistant': '{text}'", user_id))
        connection.commit()

        user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
        task = user_data[8]

        print(task)

        bot.send_message(message.chat.id, text=f"{text}")

        return text
    else:
        logging.warning(RuntimeError(
            'Invalid response received: code: {}, message: {}'.format(
                {response.status_code}, {response.text}
            )
        ))


def voice_gpt(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    try:
        tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
        user_sounds_for_sst = \
        cur.execute(f'''SELECT sounds_for_sst FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
        user_symbols_for_tts = \
        cur.execute(f'''SELECT symbols_for_tts FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
    except:
        logging.warning(f"Пользователю с id - {user_id} не удалость получить его токены")
        logging.warning(f"Пользователю с id - {user_id} не удалость получить его аудио блоки для stt")
        logging.warning(f"Пользователю с id - {user_id} не удалость получить его символы для tts")

    if tokens > MAX_TOKENS_FOR_USER:
        logging.info(f"У пользователя с id - {user_id} закончилость доступное кол-во токенов")
        bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во токенов!")

    elif user_symbols_for_tts > MAX_SYMBOLS_FOR_USER:
        bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во символов")
        logging.info(f"У пользователя с id - {user_id} закончилость доступное кол-во символов для tts")

    elif user_sounds_for_sst > MAX_SOUNDS_FOR_SST_FOR_USER:
        bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во звуковых сообщений")
        logging.info(f"У пользователя с id - {user_id} закончилость доступное кол-во аудио блоков для sst")

    elif message.content_type != "voice":
        print(message.content_type)
        bot.send_message(message.chat.id, text="Пришлите голосовое сообщение!")

    elif message.voice.duration > 15:
        bot.send_message(message.chat.id, text="Слишком длинное сообщение")
        logging.info(f"Пользователь с id - {user_id} отправил слишком длинное голосовое сообщение")

    else:
        logging.info(f"Пользователь с id - {user_id} отправил звуковое сообщение для последующей передачи его в GPT")
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        sounds_for_sst_sec = \
        cur.execute(f'''SELECT sounds_for_sst FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
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
        print(result)

        # Проверяем успешность распознавания и выводим результат
        if success:
            user_id = message.from_user.id
            connection = sqlite3.connect('database.db')
            cur = connection.cursor()

            user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
            task = user_data[8]

            sql_query = "UPDATE users_data SET task = ? WHERE user_id = ?;"
            cur.execute(sql_query, (f"{task}\n'user': {result}", user_id))
            connection.commit()

            user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
            task_2 = user_data[8]

            print(task)
            print(task_2)

            token = get_creds()
            headers = {  # заголовок запроса, в котором передаем IAM-токен
                'Authorization': f'Bearer {token}',  # token - наш IAM-токен
                'Content-Type': 'application/json'
            }
            data = {
                "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",  # указываем folder_id
                "maxTokens": MAX_TOKENS,
                "text": task
            }
            tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
            int(str(tokens))
            new_tokens = tokens + len(
                requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize", json=data,
                              headers=headers).json()['tokens'])

            sql_query = "UPDATE users_data SET tokens = ? WHERE user_id = ?;"
            cur.execute(sql_query, (new_tokens, user_id))
            connection.commit()
            tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]

            if tokens > MAX_TOKENS_FOR_USER:
                bot.send_message(message.chat.id, text="У вас закончилость доступное кол-во токенов!")
                logging.info(f"У пользователя с id - {user_id} закончилость доступное кол-во токенов")
            else:
                user_id = message.from_user.id
                connection = sqlite3.connect('database.db')
                cur = connection.cursor()

                user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
                task = user_data[8]

                print(task)

                headers = {
                    'Authorization': f'Bearer {get_creds()}',
                    'Content-Type': 'application/json'
                }
                data = {
                    "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": MAX_TOKENS
                    },
                    "messages": [
                        {
                            "role": "user",
                            "text": task
                        }
                    ]
                }

                # Выполняем запрос к YandexGPT
                response = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                                         headers=headers,
                                         json=data)

                # Проверяем, не произошла ли ошибка при запросе
                if response.status_code == 200:
                    ser_id = message.from_user.id
                    connection = sqlite3.connect('database.db')
                    cur = connection.cursor()
                    text = response.json()["result"]["alternatives"][0]["message"]["text"]

                    tokens = cur.execute(f'''SELECT tokens FROM users_data WHERE user_id = {user_id}''').fetchone()[0]
                    new_tokens = tokens + MAX_TOKENS
                    sql_query = "UPDATE users_data SET tokens = ? WHERE user_id = ?;"
                    cur.execute(sql_query, (new_tokens, user_id))

                    user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
                    task = user_data[8]

                    sql_query = "UPDATE users_data SET task = ? WHERE user_id = ?;"
                    cur.execute(sql_query, (f"{task}'\n'assistant': '{text}'", user_id))
                    connection.commit()

                    user_data = cur.execute(f'''SELECT * FROM users_data WHERE user_id = {user_id}''').fetchone()
                    task = user_data[8]

                    print(task)

                    headers = {
                        'Authorization': f'Bearer {get_creds()}',
                    }
                    data = {
                        'text': text,  # текст, который нужно преобразовать в голосовое сообщение
                        'lang': 'ru-RU',  # язык текста - русский
                        'voice': 'ermil',  # голос 
                        'folderId': folder_id,
                    }
                    # Выполняем запрос
                    response = requests.post('https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize',
                                             headers=headers, data=data)

                    if response.status_code == 200:
                        bot.send_audio(message.chat.id, response.content)
                        user_symbols_for_tts = \
                        cur.execute(f'''SELECT symbols_for_tts FROM users_data WHERE user_id = {user_id}''').fetchone()[
                            0]
                        print(user_symbols_for_tts)
                        user_symbols_for_tts_2 = user_symbols_for_tts + len(text)
                        print(user_symbols_for_tts_2)
                        sql_query = "UPDATE users_data SET symbols_for_tts = ? WHERE user_id = ?;"
                        cur.execute(sql_query, (user_symbols_for_tts_2, user_id))
                        connection.commit()
                        logging.info(f"Пользователь с id - {user_id} успешно получил ответ от GPT в формате аудио")
                        return True
                    else:
                        logging.warning("При запросе в SpeechKit возникла ошибка")
                        return False

                else:
                    logging.warning(RuntimeError(
                        'Invalid response received: code: {}, message: {}'.format(
                            {response.status_code}, {response.text}
                        )
                    ))
        else:
            bot.send_message(message.chat.id, text=f"Ошибка при распознавании речи:\n{result}")
