from py3xui import Api

# Подставьте свои данные
xui = Api("https://ваш_адрес_панели", "логин", "пароль")
xui.login()

# Проверяем доступные методы
print("Доступные методы Api:", [m for m in dir(xui) if not m.startswith('_')])

# Проверяем subscription (если есть)
if hasattr(xui, 'subscription'):
    print("Методы subscription:", [m for m in dir(xui.subscription) if not m.startswith('_')])
else:
    print("Свойство subscription отсутствует")

# Проверяем client (если есть)
if hasattr(xui, 'client'):
    print("Методы client:", [m for m in dir(xui.client) if not m.startswith('_')])
else:
    print("Свойство client отсутствует")