import json
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Creates the initial token and logs in using the api key, returns the newly opened session
def initialSetup():
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    session = requests.Session()
    session.headers.update({"accept": "application/json", "x-api-key": api_key})
    response = session.post("https://api.verkada.com/token")
    token = response.text
    session.headers.update({"x-verkada-auth": token.split('"')[3]})
    return session

# Retrieves the exception calendar IDs for every door
def retrieveExceptionIDs(session):
    response = session.get("https://api.verkada.com/access/v1/door/exception_calendar")
    doorsJson = json.loads(response.text)
    doors = doorsJson.get("door_exception_calendars", [])
    return doors

def dataFromCalendar(door, session):
    dictsFiltered = {}
    weekdayMap = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

    for doorExceptions in door.get("exceptions", []):
        singleDict = {}
       
        if doorExceptions["recurrence_rule"] != None:
            start = datetime.strptime(doorExceptions["date"] + " " + doorExceptions["start_time"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(doorExceptions["date"] + " " + doorExceptions["end_time"], "%Y-%m-%d %H:%M:%S")
            until = datetime.strptime(doorExceptions["recurrence_rule"]["until"], "%Y-%m-%d")
            name = door.get("name")
            
            if name not in dictsFiltered:
                dictsFiltered[name] = []

            if doorExceptions["recurrence_rule"] == "Daily":
                currentDate = start
                
                while currentDate <= until:
                    if currentDate.date() > datetime.now().date():
                        is_excluded = False
                        
                        if "excluded_dates" in doorExceptions:
                            exclude = doorExceptions["excluded_dates"]
                            
                            for excludeDate in exclude:
                                if datetime.strptime(excludeDate, "%Y-%m-%d").date() == currentDate.date():
                                    is_excluded = True
                                    break

                        if not is_excluded:
                            singleDict = {"door_status": doorExceptions["door_status"], "start_time": currentDate, "end_time": currentDate.replace(hour=end.hour, minute=end.minute, second=end.second)}
                            dictsFiltered[name].append(singleDict)

                    currentDate += timedelta(days=1)

            else:
                currentDate = start
                byDay = doorExceptions["recurrence_rule"].get("by_day", [])
                if not byDay:
                    byDay = [list(weekdayMap.keys())[start.weekday()]]
                target_weekdays = [weekdayMap[day] for day in byDay] 
                
                while currentDate <= until:
                    if currentDate.weekday() in target_weekdays and currentDate.date() > datetime.now().date():
                        if "excluded_dates" in doorExceptions["recurrence_rule"] and doorExceptions["recurrence_rule"]["excluded_dates"] is not None:
                            exclude = doorExceptions["recurrence_rule"]["excluded_dates"]
                            is_excluded = False
                            
                            for excludeDate in exclude:
                                if datetime.strptime(excludeDate, "%Y-%m-%d").date() == currentDate.date():
                                    is_excluded = True
                                    break

                            if not is_excluded:
                                singleDict = {"door_status": doorExceptions["door_status"], "start_time": currentDate, "end_time": currentDate.replace(hour=end.hour, minute=end.minute, second=end.second)}
                                dictsFiltered[name].append(singleDict)

                    currentDate += timedelta(days=1)
                    if currentDate.weekday() == 0 and currentDate > start:
                        currentDate += timedelta(days=(7 - (currentDate - start).days % 7) % 7)

        else:
            for key in {"door_status", "end_time", "start_time"}:
                if key in doorExceptions:
                    if key == "start_time" or key == "end_time":
                        singleDict[key] = datetime.strptime(doorExceptions["date"] + " " + doorExceptions[key], "%Y-%m-%d %H:%M:%S") # Verkada times are in UTC

                        if singleDict[key].date() < datetime.now().date():
                            break

                    else:
                        singleDict[key] = doorExceptions[key]

                    name = door.get("name")

                    if name not in dictsFiltered:
                        dictsFiltered[name] = []
            else:
                dictsFiltered[name].append(singleDict)   
    
    return dictsFiltered

# The main function that returns all the doors calendars in a dictionary
def retrieveCalendar(daystofilter = 100):
    session = initialSetup()
    doors = retrieveExceptionIDs(session)
    allDoorsCalendars = {}

    for door in doors:
        callDict = dataFromCalendar(door, session)   
        
        if callDict:
            doorKey = next(iter(callDict))
            allDoorsCalendars[doorKey] = callDict[doorKey]

    return allDoorsCalendars

if __name__ == "__main__":
    print(retrieveCalendar())
