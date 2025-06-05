import json
import pytz
import requests
import logging
import zoneinfo

from datetime import date, time, datetime, timedelta

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from collections import defaultdict
from pprint import pformat

_weights = [
    'locked',
    'access_controlled',
    'card_and_code',
    'unlocked',
]

_weekday_map = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}

# This key is used on door exception calendars to store the lists of
# exploded exception events.  We use all-caps to denote that this
# information we put on the dictionary (as opposed to information that
# was downloaded via the Verkada API).
_exploded_key = 'EXPLODED EXCEPTIONS'

# Creates the initial token and logs in using the api key, returns the
# newly opened session
def login(args):
    logging.info("Logging in to Verkada")
    session = requests.Session()
    session.headers.update({
        "accept": "application/json",
        "x-api-key": args.verkada_api_key,
    })
    response = session.post("https://api.verkada.com/token")
    st = response.status_code
    if st >= 200 and st < 300:
        all_data = json.loads(response.text)
        session.headers.update({
            "x-verkada-auth": all_data['token'],
        })
        return session

    logging.error("Verkada authentication error")
    logging.error(response.text)
    logging.error("Cannot continue")
    exit(1)

# Generic helper for Verakada API endpoints
def _get(session, endpoint):
    logging.debug(f"GET Verkada API endpoint: {endpoint}")
    response = session.get(f"https://api.verkada.com/{endpoint}")

    st = response.status_code
    if st >= 200 and st < 300:
        return response

    logging.error("Verkada API error")
    logging.error(response.text)
    logging.error("Cannot continue")
    exit(1)

# Retrieves all sites
def get_sites(session):
    logging.info("Downloading a list of Verkada sites")
    # This is somewhat unexpected: as of May 2025, v1 of the Verkada
    # API only tells us the timezone where sites are physically
    # located via the Cameras API.  So get the camera device details
    # so that we can find site IDs with corresponding timezone info.
    response = _get(session, "cameras/v1/devices")

    all_data = json.loads(response.text)
    cameras = all_data.get("cameras", [])

    # We don't care about the cameras, so strip the sites information
    # out of the cameras list and just return a list of sites.
    output = {}
    for camera in cameras:
        site_id = camera['site_id']
        if site_id not in output:
            tz = zoneinfo.ZoneInfo(camera['timezone'])
            output[site_id] = tz

    logging.debug("Transformed Verkada sites")
    logging.debug(pformat(output))

    return output

# Retrieves all doors
def get_doors(session, sites):
    logging.info("Downloading a list of Verkada doors")
    response = _get(session, "access/v1/doors")

    all_data = json.loads(response.text)
    all_doors = all_data.get("doors", [])

    logging.debug("Raw Verkada doors")
    logging.debug(pformat(all_doors))

    # Transform the doors into a dictionary indexed by door UUID.
    # Also link up the door with its corresponding timezone from the
    # sites data.
    output = {}
    for door in all_doors:
        sid = door['site']['site_id']
        if sid in sites:
            # Use an upper case key so that we know we put it there
            # (Vs. it being there in the original data we got from
            # Verkada).
            door['PYTZ'] = sites[sid]
        output[door['door_id']] = door

    logging.debug("Transformed Verkada doors")
    logging.debug(pformat(output))

    return output

# Retrieves Verkada door schedule
# There is currently no API for this, so we fake loading it (from a file)
def get_door_schedule(args, session):
    # TODO This functionality is currently not implemented.
    # Contributions would be welcomed.
    #logging.info("Downloading Verkada regular schedule")
    #with open(args.verkada_door_schedule) as fp:
    #    return json.load(fp)
    return {}

# Retrieves all exception calendars
#
# Note: There is no date range query parameters; this will download
# *all* door exception data.
def get_door_exception_calendars(session):
    logging.info("Downloading Verkada door exception calendars")
    response = _get(session, "access/v1/door/exception_calendar")

    all_data = json.loads(response.text)
    all_exception_cals = all_data.get("door_exception_calendars", [])

    logging.debug("Raw exception calendars returned from Verkada")
    logging.debug(pformat(all_exception_cals))

    # Just to be consistent with the other APIs, transform this list
    # of exception calendars into a dictionary indexed by UUID.  Also
    # convert dates and times to python objects.

    def _parse_date(text):
        return datetime.strptime(text, "%Y-%m-%d").date()

    def _parse_date_field(event, field):
        text = event[field]
        event[field] = _parse_date(text)

    def _parse_time_field(event, field):
        text = event[field]
        event[field] = datetime.strptime(text, "%H:%M:%S").time()

    output = {}
    key = 'excluded_dates'
    for exception_cal in all_exception_cals:
        for exception_event in exception_cal.get('exceptions', []):
            _parse_date_field(exception_event, 'date')
            _parse_time_field(exception_event, 'start_time')
            _parse_time_field(exception_event, 'end_time')

            rr = exception_event['recurrence_rule']
            if rr is not None:
                _parse_date_field(rr, 'until')

                # Sometimes "excluded_dates" is None, sometimes it's
                # an empty list.  Sigh.  Always make it a list of
                # python date objects.
                dates = []
                ed = rr.get(key, [])
                if ed:
                    for d in ed:
                        dates.append(_parse_date(d))
                rr[key] = dates

        output[exception_cal['door_exception_calendar_id']] = exception_cal

    return output

#-----------------------------------------------------------------

# TODO: This is currently not implemented
# Contributions would be welcomed.
def _apply_regular_schedule_to_doors(doors, schedule):
    pass

#-----------------------------------------------------------------

# The output of this function will be not-timezone-specific dates /
# times (python "naieve" date / time objects).
def _explode_exceptions(config, exceptions):

    #-----------------------------------------------------------------

    # Recurring event
    def _handle_recurring(config, event, output):
        def _handle_recurring_daily(config, event, start, end, until, output):
            logging.debug("Exploding recurring daily event")
            logging.debug(f"Start: {start}")
            logging.debug(f"Until: {until}")

            current_date = start
            one_day = timedelta(days=1)

            while current_date <= until:
                # If the date is outside the range we care about, then
                # skip it
                if current_date.date() < config['first date'] or \
                   current_date.date() > config['last date']:
                    current_date += one_day
                    continue

                ed = event['recurrence_rule']['excluded_dates']
                if current_date.date() not in ed:
                    item = {
                        "door_status": event["door_status"],
                        "start_time": current_date,
                        "end_time": current_date.replace(hour=end.hour, minute=end.minute, second=end.second)
                    }
                    output.append(item)

                current_date += one_day

        #-------------------------------------------------

        def _handle_recurring_weekly(config, event, start, end, until, output):
            logging.debug("Exploding recurring weekly event")

            current_date = start
            byDay = event["recurrence_rule"].get("by_day", [])
            if not byDay:
                byDay = [list(_weekday_map.keys())[start.weekday()]]
            target_weekdays = [_weekday_map[day] for day in byDay]

            while current_date <= until:
                if current_date.weekday() in target_weekdays and current_date.date() > datetime.now().date():
                    ed = event['recurrence_rule']['excluded_dates']
                    if current_date.date() not in ed:
                        item = {
                            "door_status": event["door_status"],
                            "start_time": current_date,
                            "end_time": current_date.replace(hour=end.hour, minute=end.minute, second=end.second)
                        }
                        output.append(item)

                current_date += timedelta(days=1)
                if current_date.weekday() == 0 and current_date > start:
                    current_date += timedelta(days=(7 - (current_date - start).days % 7) % 7)

        #-------------------------------------------------

        logging.debug("Exploding recurring event")

        start = datetime.combine(event['date'], event['start_time'])
        end = datetime.combine(event['date'], event['end_time'])
        # Until 23:59:59 on the last day
        until = datetime.combine(event['recurrence_rule']['until'],
                                 time(23, 59, 59))

        # If the repeating event is wholly outside the range we care
        # about, don't bother processing it at all.
        if until.date() < config['first date'] or \
           event['date'] > config['last date']:
            return

        frequency = event['recurrence_rule']['frequency']
        if frequency == "DAILY":
            _handle_recurring_daily(config, event, start, end, until, output)
        elif frequency == "WEEKLY":
            _handle_recurring_weekly(config, event, start, end, until, output)
        else:
            logging.error(f"Unhandled recurrence rule type: {event['recurrence_rule']}")
            logging.error("This is a programming error which must be fixed")
            exit(1)

    #-----------------------------------------------------

    # Non-recurring event
    def _handle_nonrecurring(config, event, output):
        logging.debug("Exploding non-recurring event")

        # If the date is outside the range we care about, then don't
        # add it to our list
        if event['date'] < config['first date'] or \
           event['date'] > config['last date']:
            return

        item = {
            'door_status' : event['door_status'],
            'start_time' : datetime.combine(event['date'], event['start_time']),
            'end_time' : datetime.combine(event['date'], event['end_time']),
        }

        logging.debug(f"Exploded non-recurring event: {event}")
        logging.debug(f"Converted to item: {item}")
        output.append(item)

    #-----------------------------------------------------------------

    logging.debug("Exploding each exception calendar's events...")

    # In this loop, we snip out dates that are outside of the
    # config-specified dates that we care about.

    for calendar in exceptions.values():
        exploded_events = []
        for exception_event in calendar.get('exceptions', []):
            logging.debug(f"Exploding: {pformat(exception_event)}")
            if exception_event["recurrence_rule"] is None:
                _handle_nonrecurring(config, exception_event, exploded_events)
            else:
                _handle_recurring(config, exception_event, exploded_events)

        # Add the exploded list in an ALL-CAPS name so that we know we
        # put it on the dict (vs. the data that came back from the
        # Verkada API)
        #
        # NOTE: We do not bother sorting exploded_events yet.  Since a
        # single door may have multiple exception calendars mapped to
        # it, there may be multiple exploded event lists added to a
        # door. Hence, wait until we have the final list of exploded
        # exception entries on a door before sorting that door's list.
        #
        # ADDITIONAL NOTE: we also don't bother resolving overlapping
        # events yet, for the same reason as the NOTE above.  It's
        # significantly easier to resolve overlapping events once we
        # get a final list of sorted exception events.
        calendar[_exploded_key] = exploded_events

# This function takes the not-timezone-specific dates / times and
# applies them to the specific timezones of each door to which they
# are mapped.
def _apply_exploded_exceptions_to_doors(doors, exceptions):
    logging.debug("Applying exploded lists of exceptions to each door...")

    for door in doors.values():
        door[_exploded_key] = []

    for calendar in exceptions.values():
        for door_id in calendar['doors']:
            if door_id not in doors:
                logging.error("Found an exception calendar that maps to an unknown door!")
                logging.error(f"Exception calendar: {calendar['name']} ({calendar['door_exception_calendar_id']})")
                logging.error(f"Door ID: {door_id}")
                logging.error("Skipping...")
                continue

            door = doors[door_id]
            door_tz = door['PYTZ']
            for exception_event in calendar[_exploded_key]:
                new_event = {
                    'door_status' : exception_event['door_status'],
                    'start_time' : exception_event['start_time'].replace(tzinfo=door_tz),
                    'end_time' : exception_event['end_time'].replace(tzinfo=door_tz),
                }
                door[_exploded_key].append(new_event)

    # Now that all doors have all their final exploded lists of
    # exception events (including timezone data), sort them.
    for door in doors.values():
        # If the door has no exceptions, don't sort.  It's unfortunate
        # that .sort() doesn't handle this case automatically (we'll
        # get an unknown key error from the lambda function).
        if len(door[_exploded_key]) == 0:
            continue

        door[_exploded_key].sort(key=lambda x: x['start_time'])

# Now that all the exception events on a given door have been sorted
# by start_time, find and merge overlapping exception events.
def _merge_overlapping_exceptions(doors):
    for door in doors.values():
        previous = None
        new_exception_list = []

        door_exception_events = door[_exploded_key]
        for current in door_exception_events:
            if previous is None:
                new_exception_list.append(current)
                previous = current
                continue

            if previous['end_time'].date() == current['start_time'].date() and \
               previous['end_time'] > current['start_time']:
                if previous['end_time'] >= current['end_time']:
                    if _weights.index(previous['door_status']) < _weights.index(current['door_status']):
                        new_exception_list[-1] = {
                            'door_status': previous['door_status'],
                            'start_time': previous['start_time'],
                            'end_time': current['start_time']
                        }
                        new_exception_list.append(current)
                        new_exception_list.append({
                            'door_status': previous['door_status'],
                            'start_time': current['end_time'],
                            'end_time': previous['end_time']
                        })
                        previous = new_exception_list[-1]

                    else:
                        current['start_time'] = previous['end_time']
                        if current['start_time'] < current['end_time']:
                            new_exception_list.append(current)
                            previous = current

                else:
                    if _weights.index(previous['door_status']) < _weights.index(current['door_status']):
                        new_exception_list[-1]['end_time'] = current['start_time']
                        new_exception_list.append(current)
                        previous = current

                    else:
                        current['start_time'] = previous['end_time']
                        if current['start_time'] < current['end_time']:
                            new_exception_list.append(current)
                            previous = current

            else:
                new_exception_list.append(current)
                previous = current

        door[_exploded_key] = new_exception_list

# Note: Verkada doors have site information, which, in turn, have
# timezone information corresponding to where the door is physically
# located.  Verkada door exception calendars do *not* have timezone
# information; they are assumed to apply to whatever timezone each
# door is in.
#
# In the door exception data that comes back from Verkada, recurring
# items are stored as single entries.  For ease of data handling,
# let's explode those recurring items into their full series of
# individual items.
#
# This does cost in terms of memory usage, but -- at least in this
# version of VerCalBot -- it is significantly easier to synchronize
# individual calendar events to the destination calendar than a
# recurring event which, itself, may have exceptions.
def merge_data(args, config, doors, schedule, exceptions):
    logging.info("Processing Verkada data")
    _apply_regular_schedule_to_doors(doors, schedule)
    _explode_exceptions(config, exceptions)
    _apply_exploded_exceptions_to_doors(doors, exceptions)
    _merge_overlapping_exceptions(doors)

    # Make a dictionary indexed by door name containing each door's
    # list of exception events
    output = {}
    for door in doors.values():
        output[door['name']] = door[_exploded_key]

    return output
