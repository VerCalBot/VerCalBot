#!/usr/bin/env python3

import os
import json
import logging
import argparse

from pprint import pformat

import Config
import GoogleCalendar
import Verkada

def setup_logging(args):
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO
    if args.debug:
        level = logging.DEBUG

    logging.basicConfig(level=level)

def setup_cli():
    parser = argparse.ArgumentParser()

    parser.add_argument('--config',
                        required=True,
                        help='Filename of config INI file')

    parser.add_argument('--google-creds',
                        required=True,
                        help='Google credentials JSON file')

    # TODO: This functionality is currently unimplemented.
    # Intent: Load the "regular" schedule from a JSON file because
    # -- as of May 2025 -- there's no Verkada API to download that
    # information directly from Verkada.
    # Contributions would be welcome.
    #parser.add_argument('--verkada-door-schedule',
    #                    required=True,
    #                    help='Load Verkada door schedule from this JSON file')

    default_val = os.environ.get("VERKADA_API_KEY", None)
    required_val = False if default_val else True
    parser.add_argument('--verkada-api-key',
                        required=required_val,
                        default=default_val,
                        help='Verkada API key (defaults to VERKADA_API_KEY env var, if set)')

    parser.add_argument('--dry-run',
                        action=argparse.BooleanOptionalAction)

    parser.add_argument('--verbose',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('--debug',
                        action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    setup_logging(args)

    # Sanity check
    if not os.path.exists(args.google_creds):
        logging.error(f"Cannot find {args.google_creds}")
        exit(1)

    return args

def compare(config, google_events, verkada_events):
    logging.info("Computing the difference between Google Calendar events and Verkada exceptions")
    to_delete = []
    to_add = []

    # Delete any events on the Google calendar that are not listed in
    # any Verkada events
    unused_door_names = set(google_events.keys()) - set(verkada_events.keys())
    for door_name in unused_door_names:
        to_delete.extend(google_events[door_name])
        del google_events[door_name]

    # For every door in the Verkada events:
    for door_name in verkada_events:
        # If there are no events with this door name in Google
        # Calendar, just add all the Verkada events for that door
        if door_name not in google_events:
            for event in verkada_events[door_name]:
                event["name"] = door_name

            to_add.extend(verkada_events[door_name])
            continue

        # Otherwise, we have to do a more detailed comparison.
        for ve in verkada_events[door_name]:
            found = False
            for ge in google_events[door_name]:
                # Note: both the Verkada and Google event lists
                # are sorted.  Given that there might be a lot of
                # events, we can at least take one simple shortcut
                # to cut the loop iterations.
                if ve['start_time'] > ge['start']:
                    break

                # If we find this Verkada event in the list of Google
                # events, then remove it from the list of Google
                # events and move on to the next Verkada event
                if ve["door_status"] == ge["description"] and \
                   ve["start_time"] == ge["start"] and \
                   ve["end_time"] == ge["end"]:
                    # If we did find this Verkada event, then remove
                    # it from the list of Google events so that we
                    # don't have to search it again (and we
                    # effectively mark it as "found", so that it won't
                    # be matched again).
                    google_events[door_name].remove(ge)
                    found = True
                    break

            # If we didn't find the Verkada event in the Google events
            # for this door, add it.
            if not found:
                ve["name"] = door_name
                to_add.append(ve)

        # After we're done examining all the Verkada events for this
        # door name, anything that's left in google_events for this
        # door name should be deleted
        to_delete.extend(google_events[door_name])

    logging.debug("Google events to delete from the Google Calendar")
    logging.debug(pformat(to_delete))
    logging.debug("Verkada events to add to the Google Calendar")
    logging.debug(pformat(to_add))

    return to_delete, to_add

def main():
    args = setup_cli()

    logging.info(f"Reading config: {args.config}")
    config = Config.read_config(args)

    # Get a dictionary of door names, each containing a sorted list of
    # events starting from 5 days ago.
    google_service = GoogleCalendar.login(args)
    google_events = GoogleCalendar.download(google_service, config)

    verkada_service = Verkada.login(args)
    # Get a listing of sites (which contain timezone information).
    #
    # As of May 2025, obtaining the Verkada sites (in order to get the
    # timezones where doors are physically located) requires access to
    # the Cameras APId, and therefore the API key used must have read
    # permissions on the Camera API.  This may change in future
    # Verkada functionality.
    verkada_sites = Verkada.get_sites(verkada_service)
    # Get the listing of doors, and merge in the size/timezone info
    verkada_doors = Verkada.get_doors(verkada_service,
                                      verkada_sites)
    # Get the main schedule of the doors
    verkada_schedule = \
        Verkada.get_door_schedule(args, verkada_service)
    # Get all the door exception calendars
    verkada_exceptions = \
        Verkada.get_door_exception_calendars(verkada_service)

    # Merge all the Verkada data together to get a final dictionary of
    # door names, each containing a sorted list of exception events.
    verkada_events = \
        Verkada.merge_data(args, config,
                           verkada_doors, verkada_schedule, verkada_exceptions)

    to_delete, to_add = compare(config, google_events, verkada_events)

    if len(to_delete) == 0 and len(to_add) == 0:
        logging.info("Google calendar and Verkada calendars are already in sync.  Hooray!")
    elif args.dry_run:
        # If we're in dry-run mode, just print out the changes
        logging.basicConfig(level=logging.INFO, force=True)
        logging.info("Dry run: Google events that would have been deleted")
        logging.info(pformat(to_delete))
        logging.info("Dry run: Verkada events that would have been added")
        logging.info(pformat(to_add))
    else:
        # Update the calendar
        for event in to_delete:
            logging.debug(event)
            GoogleCalendar.delete(event, google_service, config)
        for event in to_add:
            logging.debug(event)
            GoogleCalendar.add(event, google_service, config)
        logging.info("Finished synchronizing Google calendar and Verkada calendars")

if __name__ == "__main__":
    main()
