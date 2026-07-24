from py3xui import Api

# Ваши данные
PANEL_URL = "https://nl-panel.konoha.us.ci:30251/ae7kqDyXatmoYxj5KG"
PANEL_USERNAME = "Orochimaru"
PANEL_PASSWORD = "Navuhodonosor_101"

# Создаем объект Api (без verify)
xui = Api(PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD)
xui.login()

print("=" * 50)
print("Доступные методы Api:")
print("=" * 50)
methods = [m for m in dir(xui) if not m.startswith('_')]
for method in methods:
    print(f"  - {method}")

print("\n" + "=" * 50)
print("Проверка subscription:")
print("=" * 50)
if hasattr(xui, 'subscription'):
    print("✅ Свойство subscription ЕСТЬ")
    sub_methods = [m for m in dir(xui.subscription) if not m.startswith('_')]
    for method in sub_methods:
        print(f"  - {method}")
else:
    print("❌ Свойство subscription ОТСУТСТВУЕТ")

print("\n" + "=" * 50)
print("Проверка client:")
print("=" * 50)
if hasattr(xui, 'client'):
    print("✅ Свойство client ЕСТЬ")
    client_methods = [m for m in dir(xui.client) if not m.startswith('_')]
    for method in client_methods:
        print(f"  - {method}")
else:
    print("❌ Свойство client ОТСУТСТВУЕТ")

print("\n" + "=" * 50)
print("Проверка inbound:")
print("=" * 50)
if hasattr(xui, 'inbound'):
    print("✅ Свойство inbound ЕСТЬ")
    inbound_methods = [m for m in dir(xui.inbound) if not m.startswith('_')]
    for method in inbound_methods:
        print(f"  - {method}")
else:
    print("❌ Свойство inbound ОТСУТСТВУЕТ")

print("\n" + "=" * 50)
print("Проверка версии панели:")
print("=" * 50)
try:
    info = xui.get_info()
    print(f"  - Версия панели: {info.version}")
    print(f"  - Название: {info.title}")
except Exception as e:
    print(f"❌ Не удалось получить информацию: {e}")