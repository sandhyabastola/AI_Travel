import requests
from django.conf import settings

def get_weather_data(city_name):
    api_key = settings.OPENWEATHER_API_KEY
    url = "https://api.openweathermap.org/data/2.5/forecast"

    params = {
        "q": city_name,
        "appid": api_key,
        "units": "metric"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data.get("cod") != "200":
            return {"error": data.get("message", "City not found")}

        forecast_data = []
        for entry in data["list"][:5]:  # Get next 5 entries (next ~15 hours)
            forecast_data.append({
                "datetime": entry["dt_txt"],
                "description": entry["weather"][0]["description"],
                "temp": f"{entry['main']['temp']}°C"
            })

        return {
            "city": city_name,
            "forecast": forecast_data
        }

    except Exception as e:
        return {"error": str(e)}
