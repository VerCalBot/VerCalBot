import logging
import configparser

from datetime import date, timedelta

def read_config(args):
    logging.info("Reading config")
    config = configparser.ConfigParser()
    config.read(args.config)

    past_days = config.getint('General', 'days_to_schedule_in_the_past')
    future_days = config.getint('General', 'days_to_schedule_in_the_future')

    today = date.today()
    first_date = today - timedelta(days=past_days)
    last_date = today + timedelta(days=future_days)

    config_values = {
        # General
        'first date' : first_date,
        'last date' : last_date,
        'send emails': config.getboolean('General', 'send_emails'),

        # Google
        'google calendar id': config.get('Google', 'calendar_id'),

        'color unlocked': config.getint('Google', 'color_unlocked'),
        'color locked': config.getint('Google', 'color_locked'),
        'color access_controlled': config.getint('Google', 'color_access_controlled'),
        'color card_and_code': config.getint('Google', 'color_card_and_code'),

        # Email
        'sender': config.get('Email', 'sender'),
        'recipient' : config.get('Email', 'recipient'),
        'subject': config.get('Email', 'subject'),
        'body': config.get('Email', 'body'),
        'logo path': config.get('Email', 'logo_path'),
    }

    return config_values
