from mcp import Server, Tool, Response
from datetime import datetime, timedelta
import aiohttp
import os
from typing import Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

class FitnessAgent(Server):
    def __init__(self):
        super().__init__()
        self.oura_token = os.getenv('OURA_TOKEN')
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        self.creds = None
        self._load_or_refresh_google_creds()
        
    def _load_or_refresh_google_creds(self):
        """Load or refresh Google Calendar credentials"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
                
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
        
    async def initialize(self):
        """Initialize the server and register tools"""
        await super().initialize()
        
        # Register tools for external data fetching only
        self.register_tool(
            Tool(
                "get_oura_data",
                "Fetch sleep and readiness data from Oura ring",
                {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    },
                    "required": ["start_date", "end_date"]
                },
                self.get_oura_data
            )
        )
        
        self.register_tool(
            Tool(
                "get_calendar_events",
                "Fetch Google Calendar events for time period",
                {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"},
                        "calendar_id": {"type": "string", "default": "primary"}
                    },
                    "required": ["start_date", "end_date"]
                },
                self.get_calendar_events
            )
        )

    async def get_oura_data(self, params: Dict[str, Any]) -> Response:
        """Fetch sleep and readiness data from Oura API"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.oura_token}"
            }
            
            # Fetch sleep data
            sleep_url = f"https://api.ouraring.com/v2/usercollection/daily_sleep"
            params_with_dates = {
                "start_date": params["start_date"],
                "end_date": params["end_date"]
            }
            
            async with session.get(sleep_url, headers=headers, params=params_with_dates) as response:
                if response.status != 200:
                    return Response(f"Error fetching Oura sleep data: {response.status}")
                sleep_data = await response.json()
            
            # Fetch readiness data
            readiness_url = f"https://api.ouraring.com/v2/usercollection/daily_readiness"
            async with session.get(readiness_url, headers=headers, params=params_with_dates) as response:
                if response.status != 200:
                    return Response(f"Error fetching Oura readiness data: {response.status}")
                readiness_data = await response.json()
            
            return Response({
                "sleep": sleep_data["data"],
                "readiness": readiness_data["data"]
            })

    async def get_calendar_events(self, params: Dict[str, Any]) -> Response:
        """Fetch Google Calendar events for the specified time period"""
        try:
            service = build('calendar', 'v3', credentials=self.creds)
            
            # Convert dates to RFC3339 timestamp
            start_date = datetime.strptime(params["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(params["end_date"], "%Y-%m-%d") + timedelta(days=1)
            
            calendar_id = params.get("calendar_id", "primary")
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                formatted_events.append({
                    "summary": event.get('summary', 'No Title'),
                    "start": start,
                    "end": end,
                    "location": event.get('location', ''),
                    "id": event['id']
                })
            
            return Response(formatted_events)
            
        except Exception as e:
            return Response(f"Error fetching calendar events: {str(e)}")

if __name__ == "__main__":
    server = FitnessAgent()
    server.run()