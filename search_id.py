import requests
from urllib.parse import urljoin
import json

PANEL_URL = "https://nl-panel.konoha.us.ci:30251/ae7kqDyXatmoYxj5KG"
PANEL_USERNAME = "Orochimaru"
PANEL_PASSWORD = "Navuhodonosor_101"

session = requests.Session()
session.verify = False
requests.packages.urllib3.disable_warnings()

# Логин
login_url = urljoin(PANEL_URL + "/", "login")
response = session.post(login_url, data={"username": PANEL_USERNAME, "password": PANEL_PASSWORD})
print("=" * 60)
print("1. Список всех inbound'ов с их группами")
print("=" * 60)

# Получаем все inbound'ы
inbounds_url = urljoin(PANEL_URL + "/", "panel/api/inbounds/list")
response = session.get(inbounds_url)
if response.status_code == 200:
    data = response.json()
    if data.get("success"):
        inbounds = data.get("obj", [])
        print(f"Всего inbound'ов: {len(inbounds)}\n")
        for inbound in inbounds:
            print(f"  ID: {inbound.get('id')}")
            print(f"  Порт: {inbound.get('port')}")
            print(f"  Протокол: {inbound.get('protocol')}")
            print(f"  Название: {inbound.get('remark', 'без названия')}")
            print(f"  Группа (group_id): {inbound.get('group_id', 'НЕ УКАЗАНА')}")
            print("  ---")
    else:
        print("Ошибка получения inbound'ов:", data)

print("\n" + "=" * 60)
print("2. Получение списка групп (если есть отдельный эндпоинт)")
print("=" * 60)

# Пробуем получить группы
groups_url = urljoin(PANEL_URL + "/", "panel/api/groups/list")
response = session.get(groups_url)
print(f"Статус: {response.status_code}")
if response.status_code == 200:
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print("Ответ не JSON:", response.text[:500])

print("\n" + "=" * 60)
print("3. Попытка получить информацию о подписках")
print("=" * 60)

# Пробуем получить подписки
subs_url = urljoin(PANEL_URL + "/", "panel/api/subscription/list")
response = session.get(subs_url)
print(f"Статус: {response.status_code}")
if response.status_code == 200:
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print("Ответ не JSON:", response.text[:500])