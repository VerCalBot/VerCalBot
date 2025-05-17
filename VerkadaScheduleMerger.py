import datetime
import VerkadaCalendar

weights = ['locked', 'access_controlled', 'card_and_code', 'unlocked']

def mergeVerkadaSchedule():  
    currExceptions = VerkadaCalendar.retrieveCalendar()
    
    for door in currExceptions:
        currExceptions[door].sort(key=lambda x: x['start_time'])
        previous = None
        newExceptionList = []
        
        for exception in currExceptions[door]:
            if previous is None:
                newExceptionList.append(exception)
                previous = exception
                continue
                
            if previous['end_time'].date() == exception['start_time'].date() and previous['end_time'] > exception['start_time']:
                if previous['end_time'] >= exception['end_time']:
                    if weights.index(previous['door_status']) < weights.index(exception['door_status']):
                        newExceptionList[-1] = {'door_status': previous['door_status'], 'start_time': previous['start_time'], 'end_time': exception['start_time']}  
                        newExceptionList.append(exception)
                        newExceptionList.append({'door_status': previous['door_status'], 'start_time': exception['end_time'], 'end_time': previous['end_time']})
                        previous = newExceptionList[-1]           
                        
                    else:
                        exception['start_time'] = previous['end_time']
                        if exception['start_time'] < exception['end_time']:
                            newExceptionList.append(exception)
                            previous = exception
                            
                else:
                    if weights.index(previous['door_status']) < weights.index(exception['door_status']):
                        newExceptionList[-1]['end_time'] = exception['start_time']
                        newExceptionList.append(exception)
                        previous = exception
                    
                    else:
                        exception['start_time'] = previous['end_time']
                        if exception['start_time'] < exception['end_time']:
                            newExceptionList.append(exception)
                            previous = exception
                            
            else:
                newExceptionList.append(exception)
                previous = exception
        
        currExceptions[door] = newExceptionList
        
    return currExceptions
    
if __name__ == "__main__":
    print(mergeVerkadaSchedule())
