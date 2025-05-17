import datetime
import CalendarOperations
import VerkadaScheduleMerger
import json
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SERVICE_ACCOUNT = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def startup_creds():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

def dryRun():
    service = startup_creds()
    gCalendar = CalendarOperations.retrieve(service)
    vCalendar = VerkadaScheduleMerger.mergeVerkadaSchedule()
    delete, add = update(organize(gCalendar), vCalendar)
    
    print("-------Adding Events-------")
    for event in add:
        print(event["name"], "-", event["door_status"], "- Start:", event["start_time"], ", Ends:", event["end_time"])
    
    print("")
    print("-------Deleting Events-------")
    for event in delete:
        print(event["summary"], "-", event["description"], "- Start:", event["start"], ", Ends:", event["end"])

def organize(gCalendar):
    gDict = {}

    for event in gCalendar:
        event["start"] = datetime.fromisoformat(event["start"]["dateTime"]).replace(tzinfo=None)
        event["end"] = datetime.fromisoformat(event["end"]["dateTime"]).replace(tzinfo=None)

        if event["summary"] in gDict:
            gDict[event["summary"]].append(event)
        else:
            gDict[event["summary"]] = [event]

    return gDict

def update(google, verkada):
    fullDelete = []
    fullAdd = []
    
    unusedKeys = set(google.keys()) - set(verkada.keys())
    for item in unusedKeys:
        fullDelete.extend(google[item])

    for key in verkada:
        if key not in google:
            for event in verkada[key]:
                event["name"] = key
            
            fullAdd.extend(verkada[key])
        
        else:
            delete, add = change(verkada[key], google[key], key)
            fullDelete.extend(delete)
            fullAdd.extend(add)

    return fullDelete, fullAdd

def change(verkada, google, name):
    delete = []
    add = []

    for vEvent in verkada:
        for gEvent in google:
            if vEvent["door_status"] == gEvent["description"] and vEvent["start_time"] == gEvent["start"] and vEvent["end_time"] == gEvent["end"]:
                google.remove(gEvent)
                break
        else:
            vEvent["name"] = name
            add.append(vEvent)

    delete.extend(google)
    return delete, add

def pushChanges(delete, add, service):
    for event in delete:
        CalendarOperations.delete(event, service)

    for event in add:
       CalendarOperations.add(event,service)

# For testing
def delCalendar(gCalendar, service):
    for event in gCalendar:
        CalendarOperations.delete(event, service)

def run():
    try:
        service = startup_creds()
        gCalendar = CalendarOperations.retrieve(service)
        vCalendar = VerkadaScheduleMerger.mergeVerkadaSchedule()
        #delCalendar(gCalendar, service)
        pushChanges(*update(organize(gCalendar), vCalendar), service)
        
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    run()
    #dryRun()
