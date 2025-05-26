# Verkada Calendar Bot

**NOTE:** This project is not associated with the company of
[Verkada](https://www.verkada.com/) at all.  It is purely a 3rd-party
package that uses Verkada APIs.

This project reads information from Verkada Door APIs and synchronizes
the information to a Google Calendar.

# What is this project for?

The main use case for this is to allow authorized non-IT personnel to
have an easy reference to see when Verkada-controlled doors will be
unlocked, etc.

For example, say you are an IT administrator who has rights to login
to your organization's Verkada Command dashboard.  However, others in
your organization -- who don't have access to the Verkada Command
dashboard -- need to know when various doors in your facilities will be
unlocked (e.g., if the theater doors will be unlocked for a play this
evening, or the doors to the athletic facilities will be unlocked for
games this afternoon and evening).

This software will synchronize the Verkada door exceptions calendars
to a Google Calendar (probably a private, internal Google calendar) so
that authorized people can easily see when the doors will be unlocked
without needing to ask IT staff.

# Running the VerCalBot

VerCalBot is a relatively simple Python code that is desired to run
periodically to synchronize the Verkada door exceptions calendars to a
specified target Google calendar.  Specifically: running the bot will
synchronize the Verkada door exceptions calendar to the Google
calendar *right now*.  It does not run continually; you need to
periodically run the bot to react to new changes in Verkada door
exceptions calendars.

## Configuring the VerCalBot

VerCalBot requires an INI-style file with configuration values.  See
the `data/config.ini` file as an example.

Primarily, you'll want to fill in the following values:

* `days_to_schedule_in_the_past`: how many days in the past to
  synchronize to the Google Calendar
* `days_to_schedule_in_the_future`: how many days in the future to
  synchronize to the Google Calendar.
* `calendar_id`: The Google Calendar ID of the target calendar to
  synchronize.

  **NOTE:** This calendar should have nothing else on it; the bot will
  delete calendar events that it does not recognize.

Feel free to tweak the colors of events, if desired.

Additionally, you will need a Verkada API key and Google cloud
credentials.

### Verkada API key

The VerCalBot only reads from the Verkada dashboard; it never writes
anything.  Hence, it needs read-only permissions in its API key.

In the Verkada Command dashboard, navigate to:

1. Admin
1. Settings
1. API Management

Generate a new API key with the following permissions:

* Access Control: Read-Only
* Door Access Management: All Selected
* Core Command: Read-Only
* Camera Devices: Read-Only

Save the API key somewhere safe; Verkada will never show you that
value again.

### Google Cloud credentials

The VerCalBot needs to be able to write to a Google Calendar; it needs
read-write API permissions.

1. Login to the [Google Cloud Platform
   Console](https://console.cloud.google.com/).
1. Create a new Project (or select an existing one, if desired).
1. Enable the Google Calendar API.
   * Navigate to "APIs & Services" --> "Library".
   * Search for "Google Calendar API".
   * Click "Enable".
1. Create a Service Account.
   * Navigate to "APIs & Services" --> "Credentials".
   * Click "+CREATE CREDENTIALS" --> "service account".
   * Give the service account a name (e.g., `verkada-calendar-sync`).
     and an optional description.
   * Click "CREATE AND CONTINUE".
   * You can skip the "Grant User Access (Optional)" section.
   * Click "DONE".
1. Generate a Service Account Key.
   * Find the newly-created service account in the Credentials list.
   * Click on its email address.
   * Go to the "KEYS" tab.
   * Click "ADD KEY" --> "Create new key".
   * Select JSON as the key type.
   * Click "CREATE".
   * Save the downloaded JSON file securely.

## Google Calendar permissions

1. Create a Google Calendar for exclusive use by the VerCalBot.
1. Under "Share with specific people or groups", add the email address
   of the service account you just created (e.g.,
   `verkada-calendar-sync@YOUR_GCP_PROJECT.iam.gserviceaccount.com`)
1. Grant that user "Make changes to events" permissions.

## How to invoke the VerCalBot

You'll need to install the Python modules in `src/requirements.txt`.
It is suggested that you use a Python virtual environment.  For
example:

```
python3 -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt
```

The VerCalBot main executable is `src/main.py`.  It takes the
following command line arguments:

* `--config FILE`: the path name to the INI config file.
* `--google-creds`: the path name to the Google credentials file.
* `--google-calendar-id`: the ID of the Google Calendar to synchronize.
  * **NOTE:** Alternatively, this value can be passed via the
    `GOOGLE_CALENDAR_ID` environment variable (so that it is not visible
    in process listings).
* `--verkada-api-key`: the Verkada API key.
  * **NOTE:** Alternatively, this value can be passed via the
    `VERKADA_API_KEY` environment variable (so that it is not visible
    in process listings).
* `--verbose`: show some output while running (the default is to show nothing).
* `--debug`: show a *lot* of output while running.
* `--dry-run`: show what the bot *would* have done to the Google.
  Calendar, but don't actually make any changes to the Google
  Calendar.

For example, you might invoke the VerCalBot thusly:

```
source venv/bin/activate
export VERKADA_API_KEY=$(cat /path/to/your/verkada-api-key.txt)
python3 src/main.py \
    --config /path/to/your/config.ini \
    --google-creds /path/to/your/google-creds.json \
    --verbose
```

Depending on your environment, you may also have your Verkada API key
and/or Google credentials saved in a secrets management solution, and
need to extract them first.

## How often should I run the bot?

This is up to you.  Some organizations rarely change their Verkada
door exception calendars and don't mind waiting for the changes to
show up on the Google Calendar for some time; they may be comfortable
with running once a day.

Other organizations may want their Verkada door exception calendar
changes to show up quickly on the Google calendar; they may want to
run every 15 minutes, for example.

If you have your own resources, you can run the bot with whatever
frequency that you want.  Note that when you make big changes in your
Verkada schedule (e.g., you delete a 9-month long daily-recurring
event), this will take the bot a little time to reflect on the Google
calendar -- it makes an Google calendar API call to delete each
event.  Be aware of that -- e.g., you may not want to run the
VerCalBot once every minute.

### Using GitHub Actions

Synchronizing a few door exception calendars for organizations with
modest Verkada setups can probably comfortably run within the free
tier of GitHub Actions.  Running every 15 minutes throughout the
weekday workdays, for example, could be configured in a GitHub Action
YAML file like this:

```yaml
on:
    schedule:
        # GitHub Action schedules are specified in GMT;
        # hours 11-22 correspond to 6am-4pm US Eastern time
        # (for half the year)
        cron: '0,15,30,45 11-22 * * 1-5'
```

You can use the GitHub Secrets functionality to store the Verkada API
key and the Google credentials file.  For example:

1. Navigate to your repository on GitHub.
1. Navigate to "Settings" --> "Secrets and variables" --> "Actions".
1. Under "Repository secrets", click "New repository secret".
   1. Create a secret named `VERKADA_API_KEY`.
   1. Paste in the Verkada API key.
1. Repeat the procedure, pasting in the contents of the Google
   Calendar ID.
1. Repeat the procedure, pasting in the contents of the Google
   credentials file.
   1. It is recomended to store the base64-encoded version of your
      Google credentials JSON file in the GitHub Action secret.
   1. For example, run `base64 <
      /path/to/your/google-credentials.json` and paste the output into
      the GitHub Action secret.

Look at the `.github/workflows/sync.yaml` file for an example.
