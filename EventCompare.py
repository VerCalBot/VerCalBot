# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 15:49:52 2025

@author: Perrin
"""
import datetime
import event

#Function takes in two events, compares their start and end times, as well as
#the status, and if they are unequal, flags them
#I've left the function open-ended, so whether we want to replace the event
#here, or just have it flag main to replace it, it should be simple.
def compareEvent(event1, event2):
    #Checks start time
    if event1.startTime != event2.startTime:
        #TODO: Integrate with google calendar
        print("TEMP: Discrepancy detected at start")
        return 1
    #Checks end time
    if event1.endTime != event2.endTime:
        #TODO: Integrate with google calendar
        print("TEMP: Discrepancy detected at end")
        return 2
    #Checks event status
    if event1.eventType != event2.eventType:
        #TODO: Integrate with google calendar
        print("TEMP: Discrepancy detected in status")
        return 3
    #Should only be reached if everything matches.
    print("TEMP: No discrepancy")
    return 0

if __name__ == "__main__":
    start1 = datetime.datetime(2020, 5, 17, 12, 30, 00)
    end1 = datetime.datetime(2020, 5, 17, 13, 45, 1)
    start2 = datetime.datetime(2020, 5, 17, 13, 45, 1)
    end2 = datetime.datetime(2020, 5, 17, 14, 0, 0)
    start3 = datetime.datetime(2020, 5, 17, 14, 15, 0)
    end3 = datetime.datetime(2020, 5, 17, 14, 45, 0)
    event1A = event.Event(start1, end1, "Cafeteria", "Locked")
    event2A = event.Event(start2, end2, "Cafeteria", "Unlocked")
    event3A = event.Event(start3, end3, "Cafeteria", "Locked")
    start1 = datetime.datetime(2020, 5, 17, 12, 30, 00)
    end1 = datetime.datetime(2020, 5, 17, 13, 45, 1)
    start2 = datetime.datetime(2020, 5, 17, 13, 45, 1)
    end2 = datetime.datetime(2020, 5, 17, 14, 15, 0)
    start3 = datetime.datetime(2020, 5, 17, 14, 15, 0)
    end3 = datetime.datetime(2020, 5, 17, 14, 45, 0)
    event1B = event.Event(start1, end1, "Cafeteria", "Locked")
    event2B = event.Event(start2, end2, "Cafeteria", "Unlocked")
    event3B = event.Event(start3, end3, "Cafeteria", "Unlocked")
    
    compareEvent(event1A, event1B)
    compareEvent(event2A, event2B)
    compareEvent(event1A, event2A)
    compareEvent(event3A, event3B)