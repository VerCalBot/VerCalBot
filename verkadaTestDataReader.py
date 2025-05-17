# -*- coding: utf-8 -*-
"""
Created on Mon Mar 24 11:25:54 2025

@author: Perrin
"""
from datetime import datetime, timedelta
import json

def dummyVerkada():
    with open('verkadaTestData.json', 'r') as file:
        data = json.load(file)
        data = data["doors"]
        
        exportData = {}
        
        for i in data:
            name = "Door " + str(i['id']) + " - " + i['name']
            print(name)
            
            eventArray = []
            for j in i['events']:
                dayOffset = int(j['Offset'])
                
                eventStart = datetime.now()
                colon = j['start_time'].find(":")
                startHour = int(j['start_time'][0:colon])
                startMinute = int(j['start_time'][colon + 1:])
                eventStart = eventStart.replace(hour = startHour, 
                                                minute = startMinute, 
                                                second = 0, microsecond = 0)
                eventStart = eventStart + timedelta(days = dayOffset)
                
                eventEnd = datetime.now()
                colon = j['end_time'].find(":")
                endHour = int(j['end_time'][0:colon])
                endMinute = int(j['end_time'][colon + 1:])
                eventEnd = eventEnd.replace(hour = endHour, 
                                                minute = endMinute, 
                                                second = 0, microsecond = 0)
                eventEnd = eventEnd + timedelta(days = dayOffset)
                
                #print(eventStart)
                #print(eventEnd)
                
                tempDict = {'door_status' : j['status'],
                            'start_time' : eventStart,
                            'end_time' :eventEnd}
                eventArray.append(tempDict)
            exportData.update({name : eventArray})
            print(eventArray)
    return exportData
    
if __name__ == "__main__":
    userData = dummyVerkada()