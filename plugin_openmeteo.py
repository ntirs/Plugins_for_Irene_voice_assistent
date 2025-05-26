# Плагин погоды (open-meteo.com)
# author: ntirs

import os
import requests
import re
from datetime import datetime

from vacore import VACore

# Максимальное количество дней прогноза (ограничиваем для ускорения)
MAX_forecast_days = 3 

modname = os.path.basename(__file__)[:-3]  # calculating modname

# Словарь для интерпретации кодов погоды WMO
WMO_CODES = {
    0: "ясно",
    1: "в основном ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "иней",
    51: "моросящий дождь (слабый)",
    53: "моросящий дождь (умеренный)",
    55: "моросящий дождь (сильный)",
    56: "ледяной моросящий дождь (слабый)",
    57: "ледяной моросящий дождь (сильный)",
    61: "дождь (слабый)",
    63: "дождь (умеренный)",
    65: "дождь (сильный)",
    66: "ледяной дождь (слабый)",
    67: "ледяной дождь (сильный)",
    71: "снегопад (слабый)",
    73: "снегопад (умеренный)",
    75: "снегопад (сильный)",
    77: "снежные зерна",
    80: "ливневой дождь (слабый)",
    81: "ливневой дождь (умеренный)",
    82: "ливневой дождь (сильный)",
    85: "ливневой снег (слабый)",
    86: "ливневой снег (сильный)",
    95: "гроза: слабая или умеренная",
    96: "гроза с небольшим градом",
    99: "гроза с сильным градом"
}

# функция на старте
def start(core:VACore):
    manifest = { # возвращаем настройки плагина - словарь
        "name": "Прогноз погоды", # имя
        "version": "1.0", # версия
        "require_online": False, # требует ли онлайн?

        "description": "Плагин прогноз погоды\n"
                       "Голосовая команда: скажи прогноз|прогноз|какая погода",

        "options_label": {
            "weather_api_url": 'url для open-meteo.com',
            "latitude": 'широта',
            "longitude": 'долгота',
            "timezone": 'Часовой пояс',
            "forecast_days": 'Количество дней прогноза (рекомендация: от 1 до 3)'
        },

        "default_options": {
            "weather_api_url": "https://api.open-meteo.com/v1/forecast",
            "latitude": 59.939095,
            "longitude": 30.315868,
            "timezone": "Europe/Moscow", # часовой пояс
            "forecast_days": 1 # Получаем данные только на сегодня
        },

        "commands": { # набор скиллов. Фразы скилла разделены | . Если найдены - вызывается функция
            "скажи прогноз|прогноз|какая погода": get_and_speak_weather,
        }
    }
    return manifest

def start_with_options(core:VACore, manifest:dict):
    pass

def get_and_speak_weather(core: VACore, phrase: str):
    
    weather_params = {
        "daily": ["temperature_2m_max", "temperature_2m_min", "windspeed_10m_max", "pressure_msl_max", "precipitation_sum", "weathercode"], # Добавим max  температуру, давление, скорость ветра, осадки
        "current": ["temperature_2m", "windspeed_10m", "pressure_msl", "weathercode"], # Добавим текущие данные
    }

    options = core.plugin_options(modname)  # Получаем настройки    

    #params_list = []
    #params_list.append(("latitude", options["latitude"]))
    #params_list.append(("longitude", options["longitude"]))
    #params_list.append(("timezone", options["timezone"]))

    # expected_length Ожидаемая длина списков дней
    if options["forecast_days"] > MAX_forecast_days:
        expected_length = MAX_forecast_days # Ограничиваем запрос информации
    else:
        expected_length = options["forecast_days"]

    #params_list.append(("forecast_days",  expected_length))

    #for item in weather_params["daily"]:
    #    params_list.append(("daily", item))

    #for item in weather_params["current"]:
    #    params_list.append(("current", item))

    params = {
        "latitude": options["latitude"],
        "longitude": options["longitude"],
        "timezone": options["timezone"],
        "forecast_days": expected_length,
        "daily": weather_params["daily"],
        "current": weather_params["current"],
    }

    try:
      
        # Выполняем запрос к API
        response = requests.get(options["weather_api_url"], params=params)
        response.raise_for_status()  # Исключение для плохих ответов (4xx или 5xx)

        weather_data = response.json()
        #print("Полученные данные о погоде:", weather_data)  # Для отладки

        # Извлекаем необходимые данные
        current_weather = weather_data.get("current", {})
        daily_weather = weather_data.get("daily", {})
        daily_units = weather_data.get("daily_units", {})  # Получаем единицы измерения для дневных данных
        current_units = weather_data.get("current_units", {})  # Получаем единицы измерения для текущих данных

        if not current_weather:
            message = "Не удалось получить данные о текущей погоде."
            core.play_voice_assistant_speech(message)
            print(message)
            return

        weather_message_parts = []
        weather_message_parts.append("Вот данные о погоде:")

        # --- Текущая погода ---
        current_temp = int(current_weather.get("temperature_2m"))
        current_wind = int(current_weather.get("windspeed_10m"))
        current_pressure = int(current_weather.get("pressure_msl"))
        current_weather_code = current_weather.get("weathercode")
      
        # Получаем единицы измерения
        temp_unit = current_units.get("temperature_2m", "°C")
        wind_unit = current_units.get("windspeed_10m", "км/ч")
        pressure_unit = current_units.get("pressure_msl", "гПа")

        pressure_mmhg = None
        if current_pressure is not None:
            pressure_mmhg = int(current_pressure * 0.750062) # Пересчитаем в мм ртутного столба

        # Получаем описание текущей погоды по коду
        current_weather_description = WMO_CODES.get(current_weather_code, "неизвестная погода")

        # Добавляем описание текущей погоды
        if current_weather_description:
            weather_message_parts.append(f"Сейчас: {current_weather_description}.")

        if current_temp is not None:
            weather_message_parts.append(f"Температура {current_temp}{temp_unit}.")
        if current_wind is not None:
            weather_message_parts.append(f"Скорость ветра {current_wind} {wind_unit}.")
        if pressure_mmhg is not None:
            weather_message_parts.append(f"Давление {pressure_mmhg} мм ртутного столба.")

        # --- Прогноз на несколько дней (если есть) ---
         
        if daily_weather and "time" in daily_weather and len(daily_weather["time"]) >= expected_length:
            daily_message_parts = []
            
            for i in range(expected_length):
                daily_temp_max = int(daily_weather.get("temperature_2m_max", [None] * expected_length)[i])
                daily_temp_min = int(daily_weather.get("temperature_2m_min", [None] * expected_length)[i])
                daily_wind_max = int(daily_weather.get("windspeed_10m_max", [None] * expected_length)[i])
                daily_pressure_max = daily_weather.get("pressure_msl_max", [None] * expected_length)[i]
                daily_precipitation_sum = int(round((daily_weather.get("precipitation_sum", [None] * expected_length)[i])))
                daily_weather_code = daily_weather.get("weathercode", [None] * expected_length)[i]

                # Получаем описание погоды для дня из словаря
                daily_weather_description = WMO_CODES.get(daily_weather_code, "неизвестная погода")
               
                daily_pressure_mmhg = None
                if daily_pressure_max is not None:
                    daily_pressure_mmhg = int(daily_pressure_max * 0.750062)
                
                if i == 0:
                    day_text = "сегодня"
                elif i == 1:
                    day_text = "завтра"
                elif i == 2:
                    day_text = "послезавтра"

                daily_forecast = []

                # Добавляем общее описание погоды на день по weathercode
                if daily_weather_description:
                    daily_forecast.append(f"Прогноз на {day_text}: {daily_weather_description}.")

                if daily_temp_min is not None and daily_temp_max is not None:
                    daily_forecast.append(f"Температура от {daily_temp_min} до {daily_temp_max}{temp_unit}.")
                elif daily_temp_min is not None:
                    daily_forecast.append(f"Минимальная температура {daily_temp_min}{temp_unit}.")
                elif daily_temp_max is not None:
                    daily_forecast.append(f"Максимальная температура {daily_temp_max}{temp_unit}.")

                if daily_wind_max is not None:
                    daily_forecast.append(f"Максимальный ветер до {daily_wind_max} {wind_unit}.")

                if daily_pressure_mmhg is not None:
                    daily_forecast.append(f"Максимальное давление за день {daily_pressure_mmhg} мм ртутного столба.")

                # Добавляем количество осадков, если они есть (больше 0)
                if daily_precipitation_sum is not None and daily_precipitation_sum > 0:
                     precipitation_info = f"Ожидается {daily_precipitation_sum} мм осадков."
                     daily_forecast.append(precipitation_info)

                # Объединение прогнозов для каждого дня
                if daily_forecast:
                    daily_message_parts.append(" ".join(daily_forecast))

            # Объединяем части сообщения о дневном прогнозе
            if daily_message_parts:
                weather_message_parts.append("\n".join(daily_message_parts))

        # Собираем окончательное сообщение
        final_weather_message = "\n".join(weather_message_parts)

        # Озвучиваем и выводим сообщение
        final_weather_text = transform_text(final_weather_message)
        core.play_voice_assistant_speech(final_weather_text)
        print(final_weather_message)
        
    except requests.exceptions.RequestException as e:
        error_message = f"Ошибка при получении данных о погоде: {e}"
        core.play_voice_assistant_speech(error_message)
        print(error_message)
    except Exception as e:
        error_message = f"Произошла ошибка при обработке данных о погоде: {e}"
        core.play_voice_assistant_speech(error_message)
        print(error_message)


def transform_text(text):

    # Словарь для определения окончания слова "градус"
    def get_degree_ending(amount):
        if isinstance(amount, int):
            last_digit = amount % 10
            last_two_digits = amount % 100

            if last_two_digits in range(11, 15): # 11-14
                return "градусов"
            elif last_digit == 1: # 1, 21, 31...
                return "градус"
            elif last_digit in range(2, 5): # 2-4, 22-24...
                return "градуса"
            else: # 0, 5-9, 10-20, 25-30...
                return "градусов"
        else:
             # Для дробных чисел или нецелых значений лучше использовать "градусов"
             return "градусов"

    # Словарь для определения окончания слова "километр"
    def get_kilometer_ending(amount):
         if isinstance(amount, int):
            last_digit = amount % 10
            last_two_digits = amount % 100

            if last_two_digits in range(11, 15): # 11-14
                return "километров"
            elif last_digit == 1: # 1, 21, 31...
                return "километр"
            elif last_digit in range(2, 5): # 2-4, 22-24...
                return "километра"
            else: # 0, 5-9, 10-20, 25-30...
                return "километров"
         else:  # Для дробных чисел или нецелых значений
              return "километров"


    # Словарь для определения окончания слова "миллиметр"
    def get_millimeter_ending(amount):
         if isinstance(amount, int):
            last_digit = amount % 10
            last_two_digits = amount % 100

            if last_two_digits in range(11, 15): # 11-14
                return "миллиметров"
            elif last_digit == 1: # 1, 21, 31...
                return "миллиметр"
            elif last_digit in range(2, 5): # 2-4, 22-24...
                return "миллиметра"
            else: # 0, 5-9, 10-20, 25-30...
                return "миллиметров"
         else:  # Для дробных чисел или нецелых значений
              return "миллиметров"


    # Регулярное выражение и функция для градусов °C
    pattern_degrees_c = r"(\d+)\s*°C" 

    def replace_degrees_c(match):
        amount_str = match.group(1)
        try:
            amount = int(amount_str)
            ending = get_degree_ending(amount)
            return f"{amount_str} {ending} Цельсия" 
        except ValueError:
            return match.group(0)

    text = re.sub(pattern_degrees_c, replace_degrees_c, text)

    
    # Регулярное выражение и функция для километров в час km/h
    pattern_kmh = r"(\d+(\.\d+)?)\s*(?:км/ч|km/h)" 

    def replace_kmh(match):
        amount_str = match.group(1)
        try:
            # Пытаемся преобразовать число
            if '.' in amount_str:
                amount = float(amount_str)
            else:
                amount = int(amount_str)

            ending = get_kilometer_ending(amount)
            return f"{amount_str} {ending} в час"

        except ValueError:
            return match.group(0)

    text = re.sub(pattern_kmh, replace_kmh, text)


    # Регулярное выражение и функция для миллиметров осадков
    pattern_precipitation = r"(\d+(\.\d+)?)\s+мм осадков\."
  
    
    def replace_precipitation(match):
        amount_str = match.group(1)
        try:
            if '.' in amount_str:
                amount = float(amount_str)
            else:
                amount = int(amount_str)

            
            millimeter_ending = get_millimeter_ending(amount)

            return f"{amount_str} {millimeter_ending} осадков."

        except ValueError:
            return match.group(0)

    text = re.sub(pattern_precipitation, replace_precipitation, text)

    # Регулярное выражение и функция для миллиметров ртутного столба
    pattern_pressure_mmhg = r"(\d+(\.\d+)?)\s+мм ртутного столба\."

    def replace_pressure_mmhg(match):
        amount_str = match.group(1)
        try:
            if '.' in amount_str:
                amount = float(amount_str)
            else:
                amount = int(amount_str)
            
            millimeter_ending = get_millimeter_ending(amount) 

            return f"{amount_str} {millimeter_ending} ртутного столба."

        except ValueError:
            return match.group(0)


    text = re.sub(pattern_pressure_mmhg, replace_pressure_mmhg, text)

    return text