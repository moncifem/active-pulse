from typing import Any, Dict, Callable
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("fitness")

# Add OpenWeather constants
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_API_KEY = "a1873da14ab615fb26cfd2cebc294351"


async def make_oura_request(url: str, params: Dict[str, Any]) -> dict[str, Any] | None:
    """Make a request to the OURA API with proper error handling."""
    OURA_API_KEY = os.getenv("OURA_API_KEY")
    headers = {"Authorization": f"Bearer {OURA_API_KEY}"}
    params_with_dates = {"start_date": params["start_date"], "end_date": params["end_date"]}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, headers=headers, params=params_with_dates, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def get_today_and_tomorrow():
    today = datetime.today()
    tom = today + timedelta(days=1)
    formatted_today = today.strftime("%Y-%m-%d")
    formatted_tom = tom.strftime("%Y-%m-%d")
    return formatted_today, formatted_tom


def process_sleep_response(response: dict) -> str:
    data = response["data"][0]
    formatted_response = f"""
    The sleep score this night was {data["score"]} out of 100
    """
    return formatted_response


def process_activity_response(response: dict) -> str:
    data = response["data"][0]
    formatted_response = f"""
    Here are the metrics so far for today:
    
    Calories burnt: {data["active_calories"]}
    High activity minutes: {int(data['high_activity_time'])/60}
    Medium activity minutes: {int(data['medium_activity_time'])/60}
    Low activity minutes: {int(data['low_activity_time'])/60}
    Sedentary minutes: {int(data['sedentary_time'])/60}
    """
    return formatted_response


async def get_oura_data(data_type: str, processing_function: Callable, end_tomorrow: bool = False):
    url = f"https://api.ouraring.com/v2/usercollection/{data_type}"
    today, tomorrow = get_today_and_tomorrow()
    if end_tomorrow:
        end_date = tomorrow
    else:
        end_date = today
    params = {"start_date": today, "end_date": end_date}
    data = await make_oura_request(url, params)

    return processing_function(data)


@mcp.tool()
async def get_sleep_score() -> str:
    """Get the person's sleep score from last night,
    it captures how well the person slept."""
    result = await get_oura_data("daily_sleep", process_sleep_response)
    return result


@mcp.tool()
async def get_today_activity() -> str:
    """Get information about the person's activity
    so far for the day"""
    result = await get_oura_data("daily_activity", process_activity_response, end_tomorrow=True)
    return result


async def make_weather_request(url: str) -> dict[str, Any] | None:
    """Make a request to the OpenWeather API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


@mcp.tool()
async def get_paris_weather() -> str:
    """Get current weather conditions in Paris, France."""
    url = f"{OPENWEATHER_API_BASE}/weather?q=Paris,FR&appid={OPENWEATHER_API_KEY}&units=metric"
    
    data = await make_weather_request(url)
    if not data:
        return "Unable to fetch weather data for Paris"
        
    try:
        weather_desc = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        
        return f"""
Current Weather in Paris:
Temperature: {temp}°C (Feels like {feels_like}°C)
Conditions: {weather_desc.capitalize()}
Humidity: {humidity}%
Wind Speed: {wind_speed} m/s
"""
    except KeyError as e:
        return f"Error processing weather data: {str(e)}"


@mcp.tool()
async def get_workout_recommendation() -> str:
    """Get a personalized workout recommendation based on sleep quality and weather conditions."""
    # Get sleep data
    sleep_data = await get_sleep_score()
    
    # Get weather data
    weather_data = await get_paris_weather()
    
    # Combine the data into a prompt for the AI to make a recommendation
    context = f"""
Based on the following data, suggest a suitable workout plan for today:

Sleep Information:
{sleep_data}

Weather Information:
{weather_data}

Please provide a workout recommendation considering:
1. Sleep quality (higher sleep scores allow for more intense workouts)
2. Weather conditions (suggest indoor activities if weather is poor)
3. Temperature (adjust intensity based on heat/cold)
"""
    
    return context


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
