###################################################################################
import os                                                                         #
import asyncio                                                                    #
import requests                                                                   #
from dotenv import load_dotenv                                                    #
from aiogram import Bot, Dispatcher, types, F                                     #
from aiogram.filters import Command, CommandStart                                 #
from aiogram.types import Message                                                 #
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application#
from aiohttp import web                                                           #
                                                                                  #
# Загрузка токена                                                                 #
load_dotenv()                                                                     #
TOKEN = os.getenv("TOKEN")                                                        #
API_KEY = os.getenv("API_KEY")                                                    #
WEBHOOK_URL = os.getenv("WEBHOOK_URL")                                            #
bot = Bot(token=TOKEN)                                                            #
dp = Dispatcher()                                                                 #
WEBHOOK_PATH = "/webhook"                                                         #
                                                                                  #
###################################################################################

from datetime import datetime, timedelta, timezone

CITIES = ['Москва', 'Санкт-Петербург', 'Рига', 'Севастополь']


def get_weather_report(city):
    output = f"=== {city} ===\n"
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
    weather_resp = requests.get(weather_url).json()
    
    if 'main' in weather_resp:
        desc = weather_resp['weather'][0]['description'].capitalize()
        temp = weather_resp['main']['temp']
        timezone_offset = weather_resp.get('timezone', 0)
        local_time = datetime.now(timezone.utc) + timedelta(seconds=timezone_offset)
        time_str = local_time.strftime('%Y-%m-%d %H:%M')

        output += "Местное время:       " + time_str + "\n"
  #      output += f"Сейчас: {desc}, {temp}°C\n"
        output += "Сейчас:                         " + str(desc) + "   " + str(temp) + "°C\n"
    else:
        return f"{city}: ошибка погоды: {weather_resp.get('message', 'Нет данных')}"

    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&lang=ru"
    forecast_resp = requests.get(forecast_url).json()

    today_min_temp = float('inf')
    today_max_temp = float('-inf')
    tomorrow_min_temp = float('inf')
    tomorrow_max_temp = float('-inf')

    if 'list' in forecast_resp:
        today_forecast_output = "\nПрогноз на сегодня по часам:\n"
        tomorrow_date = (datetime.now(timezone.utc) + timedelta(days=1)).date()
        today_date = datetime.now(timezone.utc).date()
        timezone_offset_city = forecast_resp.get('city', {}).get('timezone', timezone_offset)

        found_today_data = False

        for entry in forecast_resp['list']:
            utc_dt = datetime.fromtimestamp(entry['dt'], tz=timezone.utc)
            local_dt = utc_dt + timedelta(seconds=timezone_offset_city)
            entry_date = local_dt.date()
            time_str = local_dt.strftime('%H:%M')
            desc = entry['weather'][0]['description'].capitalize()
            temp = entry['main']['temp']

            # Прогноз по часам на сегодня
            if entry_date == today_date:
                today_forecast_output += f"{time_str} — {desc}, {temp}°C\n"
                found_today_data = True
                today_min_temp = min(today_min_temp, temp)
                today_max_temp = max(today_max_temp, temp)
            elif entry_date == tomorrow_date:
                tomorrow_min_temp = min(tomorrow_min_temp, temp)
                tomorrow_max_temp = max(tomorrow_max_temp, temp)

        if found_today_data:
            output += today_forecast_output
        else:
            output += "\nНет данных на сегодня.\n"

        # Минимальная и максимальная температура на завтра
        if tomorrow_min_temp != float('inf') and tomorrow_max_temp != float('-inf'):
            output += f"\nЗавтра мин./макс. температура: {tomorrow_min_temp}°C / {tomorrow_max_temp}°C\n"
        else:
            output += "\nНет данных на завтра.\n"
    else:
        output += "\nОшибка прогноза: " + forecast_resp.get('message', 'Нет данных') + "\n"

    return output.strip()



@dp.message(CommandStart())
@dp.message(Command("weather"))
async def handle_start(message: Message):
    await message.answer("Получаю данные, подождите...")
    for city in CITIES:
        try:
            report = get_weather_report(city)
            await message.answer(report)
            await asyncio.sleep(0.2)
        except Exception as e:
            await message.answer(f"Ошибка при получении данных по {city}: {e}")


# === WEBHOOK ===
     

async def on_startup(bot: Bot):
    print("Setting up webhook...")
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    print(f"Webhook URL: {webhook_url}")
    try:
        await bot.set_webhook(webhook_url)
        print(f"Webhook set successfully to {webhook_url}")
    except Exception as e:
        print(f"Failed to set webhook: {e}")


async def main():
    # Настройка веб-приложения
    app = web.Application()
    
    # Создаем обработчик вебхуков
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    
    # Регистрируем обработчик по указанному пути
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Монтируем диспетчер в приложение
    setup_application(app, dp, bot=bot)
    
    # Запускаем веб-сервер
    return app

if __name__ == '__main__':
    if os.getenv('RENDER'):
        # Настройка для Render
        app = asyncio.run(main())
        web.run_app(app, host="0.0.0.0", port=10000)
    else:    
        # Локальный запуск с polling
        asyncio.run(dp.start_polling(bot))
        