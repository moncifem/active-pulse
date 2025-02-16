from typing import Any, Dict, Callable
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("fitness")


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


def get_yesterday_and_today():
    today = datetime.today()
    yesterday = today + timedelta(days=-1)
    formatted_today = today.strftime("%Y-%m-%d")
    formatted_yesterday = yesterday.strftime("%Y-%m-%d")
    return formatted_yesterday, formatted_today


def process_sleep_response(response: dict) -> str:
    data = response["data"][0]
    formatted_response = f"""
    The sleep score this night was {data["score"]} out of 100
    """
    return formatted_response


async def get_oura_data(data_type: str, processing_function: Callable):
    url = f"https://api.ouraring.com/v2/usercollection/{data_type}"
    _, today = get_yesterday_and_today()
    params = {"start_date": today, "end_date": today}
    data = await make_oura_request(url, params)

    return processing_function(data)


@mcp.tool()
async def get_sleep_score() -> str:
    """Get the person's sleep score from last night,
    it captures how well the person slept."""
    result = await get_oura_data("daily_sleep", process_sleep_response)
    return result


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
