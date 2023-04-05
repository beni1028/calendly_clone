import json
from uuid import uuid4
from datetime import datetime
from typing import List, Dict

from django.conf import settings
from django.utils import timezone as tz

from scheduler.hook_authentication import WebhookToken

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GoogleCalendar():

    def __init__(self, calendar_auth):
        self.update_access_token(calendar_auth["refresh_token"])
    
    def update_access_token(self, refresh_token):
        """
        Use the refresh token existing in calendar_auth to fetch the access_token.
        """

        SCOPES = ['https://www.googleapis.com/auth/calendar',
                  'https://www.googleapis.com/auth/userinfo.email', 
                  'https://www.googleapis.com/auth/userinfo.profile', 'openid']
        credentials = Credentials(
            token=refresh_token,
            refresh_token=refresh_token,
            token_uri=settings.GOOGLE_TOKEN_URL,
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=SCOPES
        )

        service = build('oauth2', 'v2', credentials=credentials, cache_discovery=False)
        user_info = service.userinfo().get().execute()

        self.google_access_token = credentials.token
        self.google_refresh_token = credentials.refresh_token

    # def _get_reminders

    def _get_attendees_list(self, attendees: List) -> List[Dict]:
        attendees_list = []
        if attendees:
            for attendee in attendees_list:
                attendees_list.append({'email': attendee})
        return attendees_list

    def create_event_data(self, summary, location, start_data_time,
                          end_date_time, attendees_emails=None,
                          reminders=None, description="",
                          timezone=None, send_notifications=True):
        """
        Create event data dict that allows google calendar to create events
        - start_data_time and end_date_time example: '2022-10-06T17:30:00'
        - attendees_emails - List of emails of attendees
        - reminders Example - [{'method': 'popup', 'minutes': 10}, ...]
        - by default always creates and adds a meet link to G-calendar
        """

        if location is None:
            location = ''

        if timezone is None:
            timezone = str(tz.get_default_timezone())

        # reminders_object = {'useDefault': True}

        if not reminders:
            reminders_object = {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ]}
        else:

            reminders_object = {
                'useDefault': False,
                'overrides': reminders
            }

        calendar_data = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_data_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_date_time.isoformat(),
                'timeZone': timezone,
            },
            'reminders': reminders_object,
            "sendNotifications": send_notifications,
            "conferenceData": {
                                    "createRequest": {
                                        "requestId": f"{uuid4().hex}",
                                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                                    }
                                },
        }
        if attendees_emails:
            attendees_list = []
            for attendee in attendees_emails:
                attendees_list.append({'email': attendee})

        return True, calendar_data

    def get_calendar_service(self):
        '''
        Uses credentials from global to create credential service
        '''

        creds = Credentials(
            self.google_access_token,
            refresh_token=self.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="145373107593-idm4tsav2prfhs4u2nht08t7brh3e6c0.apps.googleusercontent.com",
            client_secret="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",
            scopes=["https://www.googleapis.com/auth/calendar", 
                    "https://www.googleapis.com/auth/calendar.events"]
        )

        service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        return service

    def create_calendar_event(self, event_data):
        '''
        Create calendar event
        @params event_data - The event dict as comes form `create_event_data`
        '''

        try:
            service = self.get_calendar_service()
            event = service.events().insert(
                calendarId='primary',
                body=event_data, sendUpdates='all',
                conferenceDataVersion=1).execute()

            event_link = event.get('htmlLink')
            event_id = event.get('id')

            return {
                'created': True,
                'event_link': event_link,
                'event_id': event_id,
                'location': event["location"]
                if event.get("location")
                else event.get("hangoutLink"),
            }

        except Exception as e:
            print("Exception came while creating event: ", e)
            return {
                'created': False,
                'error': e
            }

    def retrieve_calendar_event(self, event_id):
        try:
            service = self.get_calendar_service()
            event = service.events().get(calendarId='primary', eventId=event_id).execute()

            event.update({'read': True, 'event_id': event_id})
            return event

        except Exception as e:
            print("Exception came while retrieving event: ", e)
            return {
                'read': False,
                'error': e
            }

    def update_calendar_event(self, event_id, event_data):
        # First retrieve the event from the API.
        try:
            service = self.get_calendar_service()
            event = service.events().get(calendarId='primary', eventId=event_id).execute()

            for key in event_data:
                event[key] = event_data[key]

            updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
            return {
                'updated': True,
                'event_link': updated_event.get('htmlLink'),
                'event_id': event_id
            }

        except Exception as e:
            print("Exception came while updating event: ", e)
            return {
                'updated': False,
                'error': e
            }

    def delete_calendar_event(self, event_id):
        ''' Deletes the specified calendar event from google calendar '''

        try:
            service = self.get_calendar_service()
            service.events().delete(calendarId='primary', eventId=event_id).execute()

            return {
                'deleted': True,
                'event_id': event_id
            }
        except Exception as e:
            print("Exception came while deleting the event: ", e)

            # It can happen that the resouce is already deleted,
            # deleting in that case throws an error
            already_deleted = False
            try:
                content = e.__dict__.get('content')
                body = json.loads(content)
                if body.get('error').get('code') == 410:
                    already_deleted = True
            except:
                pass

            return {
                'deleted': False,
                'already_deleted': already_deleted,
                'error': e
            }

    def is_events_list(self, datetime_min, datetime_max, timeZone=None, **kwargs):
        ''' 
        Example
        - time_min: 2022-10-12T21:00:00 (datetime object)
        - time_max: 2022-10-12T22:00:00 (datetime object)
        '''

        try:

            service = self.get_calendar_service()
            events_result = service.events().list(
                calendarId='primary',
                timeMin=datetime_min, timeMax=datetime_max).execute()

            events = events_result.get('items', [])

            event_timings = []
            for event in events:
                event_timings.append({
                    'id': event['id'],
                    "start": datetime.strptime(event["start"]["dateTime"], '%Y-%m-%dT%H:%M:%S%z'),
                    "end": datetime.strptime(event["end"]["dateTime"], '%Y-%m-%dT%H:%M:%S%z'),
                })
            
            return {
                "success": True,
                "events": event_timings
            }

        except Exception as e:
            print("Exception came while trying to find a free slot, error: ", e)
            return {
                'success': False,
                'error': e
            }

    def activate_webhook(self, event_id, unique_id, start_time):
        '''
        Reference: https://developers.google.com/calendar/api/guides/push
        '''
        url_path = 'accounts/webhook/event-update/<uid>/'
        token = get_token_(url_path)


        callback_url = f"{settings.BACKEND_URL}events/webhook/event-update/{event_id}/"
        try:
            service = self.get_calendar_service()
            body = {
                'id': unique_id,
                'type': 'webhook',
                'address': callback_url,
                'expiration': int((start_time).timestamp() * 1000),
                'payload': True,
                'params': {
                    'auth_token': settings.GOOGLE_CALENDAR_EVENT_WEBHOOK_TOKEN,
                },
                'ttl': 3600,
                'channel': {
                    'type': 'web_hook',
                    'address': callback_url,
                }
            }

            webhook_response = service.events().watch(calendarId='primary', body=body).execute()
            print(webhook_response)
            return {
                'success': True,
                'event_id': event_id
            }

        except Exception as err:
            print("Exception came while activating the event's webhook: ", err)
            return {
                'success': False,
                'error': err
            }

    def deactivate_webhook(self, webhook_uid, resource_id):
        '''
        Reference: https://developers.google.com/calendar/api/guides/push
        '''
        try:
            service = self.get_calendar_service()
            service.channels().stop(body={"id": webhook_uid, "resourceId": resource_id}).execute()
            return {
                'deactivated': True
            }
        except Exception as err:
            print("Exception came while deactivating the event's webhook: ", err)
            return {
                'deactivated': False,
                'error': err
            }
