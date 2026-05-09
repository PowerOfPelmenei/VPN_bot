import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PANEL_HOST = os.getenv("PANEL_HOST")
PANEL_USERNAME = os.getenv("PANEL_USERNAME")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")

INBOUND_REMARKS = [
    "VLESS TCP REALITY",
    "VLESS XHTTP REALITY",
    "TROJAN TCP",
    "TROJAN WS",
    "TROJAN gRPC"
]

LINK_TEMPLATES = {
    "VLESS TCP REALITY": "vless://{uuid}@ru-panel.konoha.us.ci:443?type=tcp&encryption=none&security=reality&pbk"
                         "=DduZDuJsYdOaqxnX7eQHHQn4cPQ6nRDB2kmoDXYZG1g&fp=chrome&sni=rbc.ru&sid=61f54bfb316d&spx=%2F"
                         "&flow=xtls-rprx-vision#{remark_suffix}",
    "VLESS XHTTP REALITY": "vless://{uuid}@ru-panel.konoha.us.ci:8443?type=xhttp&encryption=none&path=%2F&host=&mode"
                           "=auto&x_padding_bytes=100-1000&extra=%7B%22xPaddingBytes%22%3A%22100-1000%22%7D&security"
                           "=reality&pbk=57qwxdjJCBfMS5nAdocb82Hw5fl4NP1vDnY4ISDxoGk&fp=chrome&sni=rbc.ru&sid"
                           "=61f54bfb316d&spx=%2F#{remark_suffix}",
    "TROJAN TCP": "trojan://{uuid}@ru-panel.konoha.us.ci:9001?type=tcp&security=none#{remark_suffix}",
    "TROJAN WS": "trojan://{uuid}@ru-panel.konoha.us.ci:9002?type=ws&path=%2Ftrojan_ws&host=&security=none#{"
                 "remark_suffix}",
    "TROJAN gRPC": "trojan://{uuid}@ru-panel.konoha.us.ci:9003?type=grpc&serviceName=trojan-grpc&authority=&security"
                   "=none#{remark_suffix}",
}

PRICES = {1: 300, 3: 600}  # Цены на тариф в звездах
DAYS_MAP = {1: 30, 3: 90}  # Длительность тарифовв
FREE_TRIAL_DAYS = 3  # Длительность тестоввого тарифа
TEST_DAYS = 30  # для команды /test, проверки бота

DB_PATH = "vpn_bot.db"
ADMIN_IDS = [1426184917]
