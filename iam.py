from info import *
from kit_speach import *
import requests
import time
import json
from datetime import datetime
import logging



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
    encoding='utf-8',
)


MAX_USERS = 3
MAX_SYMBOLS_FOR_USER = 600
MAX_TOKENS_FOR_USER = 600
MAX_SOUNDS_FOR_SST_FOR_USER = 20
MAX_TOKENS = 60


def create_new_token():
    logging.info("Создан iam токен")
    url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {
        "Metadata-Flavor": "Google"
    }
    try:
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            token_data = response.json()  # вытаскиваем из ответа iam_token
            # добавляем время истечения iam_token к текущему времени
            token_data['expires_at'] = time.time() + token_data['expires_in']
            # записываем iam_token в файл
            with open("IAM_TOKEN", "w") as token_file:
                json.dump(token_data, token_file)
    except Exception as e:
        print(f"Ошибка получения iam_token: {e}")


def get_creds():
    try:
        # чтение iam_token
        with open("IAM_TOKEN", 'r') as f:
            file_data = json.load(f)
            expiration = datetime.strptime(file_data["expires_at"][:26], "%Y-%m-%dT%H:%M:%S.%f")
        # если срок годности истёк
        if expiration < datetime.now():
            logging.info("Срок годности iam_token истёк")
            # получаем новый iam_token
            create_new_token()
    except:
        # если что-то пошло не так - получаем новый iam_token
        create_new_token()

    # чтение iam_token
    with open("IAM_TOKEN", 'r') as f:
        file_data = json.load(f)
        iam_token = file_data["access_token"]

    print(iam_token)
    return iam_token
