from py3xui import XUI

# Подставьте свои данные
xui = XUI("https://nl-panel.konoha.us.ci:30251/ae7kqDyXatmoYxj5KG", "Orochimaru", "Navuhodonosor_101")
xui.login()

# Проверяем, есть ли методы для подписок
print("Доступные методы:", [m for m in dir(xui) if not m.startswith('_')])
print("\nМетоды subscription:", [m for m in dir(xui.subscription) if not m.startswith('_')])