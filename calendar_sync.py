import os
import json
import datetime
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_NAME = "AITU Schedule - Trimester 3"

def get_client_config():
    """Returns the Google Cloud Client config from Streamlit Secrets or a local file."""
    if "GCP_CREDENTIALS_JSON" in st.secrets:
        return json.loads(st.secrets["GCP_CREDENTIALS_JSON"])
    else:
        # Fallback to local file for development
        with open('credentials_web.json', 'r') as f:
            return json.load(f)

def get_auth_url(redirect_uri="http://localhost:8501/"):
    """Generates the Google OAuth authorization URL for web flow."""
    client_config = get_client_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return auth_url, state

def get_credentials_from_code(code, redirect_uri="http://localhost:8501/"):
    """Exchanges the authorization code for credentials."""
    client_config = get_client_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code)
    return flow.credentials

def get_calendar_service(creds):
    """Builds the service directly from provided credentials."""
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_or_create_calendar(service, name=CALENDAR_NAME):
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == name:
                return calendar_list_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

    calendar = {
        'summary': name,
        'timeZone': 'Asia/Almaty'
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    return created_calendar['id']

def insert_schedule_events(service, calendar_id, selected_events):
    # selected_events is a list of dicts: {'Group': '...', 'Day': 'Monday', 'Time': '18:00-18:50', 'Discipline': '...', 'Classroom': '...', 'Type': '...', 'Lecturer': '...'}
    day_mapping = {
        'Monday': '2026-03-09',
        'Tuesday': '2026-03-10',
        'Wednesday': '2026-03-11',
        'Thursday': '2026-03-12',
        'Friday': '2026-03-13',
        'Saturday': '2026-03-14',
        'Sunday': '2026-03-15',
    }
    
    # Google Calendar supports 11 predefined event colors (colorId '1' through '11')
    available_color_ids = [str(i) for i in range(1, 12)]
    discipline_colors = {}
    
    events_created = []
    
    for ev in selected_events:
        day_str = ev.get('Day', '').strip()
        time_str = ev.get('Time', '').strip()
        discipline = ev.get('Discipline', '')
        
        if day_str not in day_mapping or not time_str:
            continue
            
        base_date = day_mapping[day_str]
        
        # Parse time (e.g., '18:00-18:50')
        parts = time_str.split('-')
        if len(parts) != 2:
            continue
            
        start_time, end_time = parts[0].strip(), parts[1].strip()
        # Formulate RFC3339 datetime
        start_datetime = f"{base_date}T{start_time}:00+05:00"
        end_datetime = f"{base_date}T{end_time}:00+05:00"
        
        # Assign a consistent colorId per discipline
        if discipline not in discipline_colors:
            discipline_colors[discipline] = available_color_ids[len(discipline_colors) % 11]
            
        event = {
            'summary': discipline,
            'location': ev.get('Classroom', ''),
            'description': f"Group: {ev.get('Group', 'Unknown')}\nType: {ev.get('Type', '')}\nLecturer: {ev.get('Lecturer', '')}",
            'colorId': discipline_colors[discipline],
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'Asia/Almaty',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'Asia/Almaty',
            },
            'recurrence': [
                'RRULE:FREQ=WEEKLY;UNTIL=20260517T000000Z'
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        events_created.append(created_event['id'])
            
    return events_created
