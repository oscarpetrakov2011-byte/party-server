# Party Mod Server

WebSocket сервер для мода Party в Minecraft.

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python party_server.py
```

Сервер запустится на порту 8765.

## Деплой на Render.com

1. Создайте аккаунт на https://render.com
2. Нажмите "New +" -> "Web Service"
3. Подключите этот GitHub репозиторий
4. Настройки:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python party_server.py`
5. Нажмите "Create Web Service"

После деплоя вы получите URL вида: `wss://your-app.onrender.com`

Замените в моде адрес `ws://localhost:8765` на ваш новый URL.
