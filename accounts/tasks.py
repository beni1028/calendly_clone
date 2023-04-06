from django.core.mail import send_mail
from django.conf import settings

from celery import shared_task
from scheduler.celery import create_perodic_task

from .calendar import GoogleCalendar
from .models import Events, CalendarEvents


def get_payload_parameters(calender_event, event):
    calendar_data = {
        "summary": event.title,
        "location": event.location,
        "description": event.description,
        "start_data_time": calender_event.start_datetime,
        "end_date_time": calender_event.end_datetime,
        "reminders": True,
        "attendees_emails": calender_event.attendees
    }
    return calendar_data


@shared_task
def create_calender_event(calender_event_id):

    calendar_event = CalendarEvents.objects.get(id=calender_event_id)
    event = Events.objects.get(id=calendar_event.event.id)
    calendar_client = GoogleCalendar(event.created_by.calendar_auth)

    # Get the required payload variables
    calendar_data = get_payload_parameters(calendar_event, event)

    # Generate payload
    valid, calendar_event_data = calendar_client.create_event_data(
        **calendar_data
        )

    if not valid:
        print("LOGGING: reminders object not valid, error: ",
              calendar_event_data)
        return False

    google_calendar_event = None

    if not calendar_event.uid:
        new_event = True
        google_calendar_event = calendar_client.create_calendar_event(calendar_event_data)
        calendar_event.uid = google_calendar_event.get('event_id')
        calendar_event.event_link = google_calendar_event.get('event_link')
        calendar_event.location = google_calendar_event.get('location')
    else:
        # Update the event with uid
        google_calendar_event = calendar_client.update_calendar_event(
            calendar_event.uid,
            calendar_event_data)
        print(google_calendar_event)
        new_event = False
        
        if not google_calendar_event.get('updated'):
            print("Event updation failed", google_calendar_event)
            return False

    print("herere")

    super(calendar_event.__class__, calendar_event).save()

    # XXX: May be exit the the funtion above
    # and create a separate task for hooks

    if not calendar_event.webhook_uid or new_event:
        if not new_event:
            calendar_client.deactivate_webhook(
                calendar_event.webhook_uid,
                calendar_event.webhook_data["X-Goog-Resource-Id"])

        calendar_event.generate_webhook_uid()

        web_hook_response = calendar_client.activate_webhook(
            calendar_event.uid,
            calendar_event.webhook_uid,
            calendar_event.start_datetime)

        if not web_hook_response.get("success"):
            calendar_event.webhook_uid = None
    super(calendar_event.__class__, calendar_event).save()
    # trigger reminders
    return True

@shared_task
def update_slots(event_slug, remove_slots, add_slots_back=None):
    event = Events.objects.get(slug=event_slug)
    key_to_remove = next(iter(remove_slots))
    event.slots.pop(key_to_remove)
    print(len(event.slots))
    if add_slots_back:
        event.slots.update(add_slots_back)
    print(len(event.slots))
    event.save()
    print(len(event.slots))
    return


@shared_task
def delete_event_from_calendar(calender_event_id):
    calendar_event = CalendarEvents.objects.get(id=calender_event_id)
    calendar_client = GoogleCalendar(calendar_event.event.created_by.calendar_auth)

    calendar_client.delete_calendar_event(calendar_event.uid)

    if calendar_event.webhook_uid:
        calendar_client.deactivate_webhook(
            calendar_event.webhook_uid,
            calendar_event.webhook_data["X-Goog-Resource-Id"]
            )
    
        # clean up event data and mark it deleted
    calendar_event.location = calendar_event.uid = calendar_event.event_link =\
        calendar_event.webhook_uid = calendar_event.webhook_data = None
    
    calendar_event.save(call_super=True)

    return

@shared_task
def send_booking_email(email_list, event_slug):
    try:
        subject = 'Verify Your Account'
        html_message = f"Please click on the link to book a meeting slot:\
                                  {settings.BACKEND_URL}accounts/event-slots/{event_slug}/"
        from_email = 'noreply@example.com'
        send_mail(subject, html_message, from_email, email_list)
        return True
    
    except Exception as err:
        print(f"Excption came while trying to send Booking Email. Error:{err}")
        return False

@shared_task
def schedule_reminders(calender_event_id, reminder_schedule):
    calender_event = CalendarEvents.objects.get(id = calender_event_id)

    for channel, duration in reminder_schedule.items():
        
        reminder_scheduled_at = event_starttime - timezone.timedelta(minutes=duration)

        reminder_scheduled_at_str = reminder_scheduled_at.strftime("%I:%M %p %b %d, %Y")

        reminder_task_name = f"Event Reminder Task | "\
                        f"Calender_Event_ID: {calendar_event.id} | "\
                        f"Reminder_Type: {channel} | "\
                        f"Scheduled_at: {reminder_scheduled_at_str}"

        reminder_task = create_perodic_task(
            send_event_reminder, reminder_task_name, reminder_scheduled_at,
            {"channel": channel, "calendar_event_id": calender_event_id,
             "event_title": calender_event.event.title, 
             "host": calender_event.event.created_by})# created by shuld be replaced by name
    
    calendar_event.tasks.add(reminder_task)

@shared_task
def send_event_reminder(channel, calender_event_id, event_title, host):
    if channel == "email":
        try:
            subject = f'Reminder for {event_title} with {host}'
            html_message = f""
            from_email = 'noreply@example.com'
            send_mail(subject, html_message, from_email, email_list)
            return True
    
        except Exception as err:
            print(f"Excption came while trying to send Booking Email. Error:{err}")
            return False
            pass