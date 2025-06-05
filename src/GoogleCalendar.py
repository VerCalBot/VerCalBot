import os
import logging

from pprint import pformat
from collections import defaultdict
from datetime import datetime, timezone, timedelta, time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def login(args):
    logging.info("Logging in to Google")
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = service_account.Credentials.from_service_account_file(args.google_creds, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds,
                 cache_discovery=False)

def download(service, args, config):
    first_date = datetime.combine(config['first date'],
                                  time(0, 0, 0),
                                  tzinfo=timezone.utc).isoformat()
    last_date = datetime.combine(config['last date'],
                                 time(23, 59, 59),
                                 tzinfo=timezone.utc).isoformat()
    logging.info(f"Downloading Google Calendar events between {first_date} and {last_date}...")

    output = defaultdict(list)
    page_token = None
    while True:
        events_result = (
            service.events()
            .list(calendarId=args.google_calendar_id,
                  timeMin=first_date,
                  timeMax=last_date,
                  # Expand recurring events into separate instances rather
                  # than grouping them
                  singleEvents=True,
                  orderBy="startTime",
                  pageToken=page_token,
                  maxResults=2500,
                  fields="items(summary,id,description,start,end,colorId)"
                  )
            .execute()
        )

        new_events = events_result.get('items', [])
        if not new_events:
            break

        # Gather events by summary (i.e., door name)
        for event in new_events:
            # Google calendar events are returned in UTC. Convert them
            # to python datetimes.
            dt = datetime.fromisoformat(event['start']['dateTime'])
            event['start'] = dt.astimezone(timezone.utc)
            dt = datetime.fromisoformat(event['end']['dateTime'])
            event['end'] = dt.astimezone(timezone.utc)
            output[event["summary"]].append(event)

        # Continues to process events if there are more to process
        page_token = events_result.get('nextPageToken')
        if not page_token:
            break

    logging.debug("Google Calendar events downloaded")
    logging.debug(pformat(output))

    return output

def add(verkada_event, service, args, config):
    logging.info(f"Adding Google Calendar event: {verkada_event['name']} / {verkada_event['door_status']}, starting {verkada_event['start_time']}")

    color = config[f'color {verkada_event["door_status"]}']

    google_event = {
        "summary": verkada_event["name"],
        "start": {
            "dateTime": verkada_event["start_time"].isoformat(),
        },
        "end": {
            "dateTime": verkada_event["end_time"].isoformat(),
        },
        "description": verkada_event["door_status"],
        "colorId": color,
    }

    service.events().insert(calendarId=args.google_calendar_id,
                            body=google_event).execute()

def delete(google_event, service, args, config):
    desc = google_event.get('description', '')
    logging.info(f"Removing Google Calendar event: {google_event['summary']} / {desc}, starting {google_event['start']}")

    service.events().delete(calendarId=args.google_calendar_id,
                            eventId=google_event["id"]).execute()
