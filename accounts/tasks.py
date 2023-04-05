from celery import shared_task

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

    if not calendar_event.uid:
        new_event = True
        event = calendar_client.create_calendar_event(calendar_event_data)
        calendar_event.uid = event.get('event_id')
        calendar_event.event_link = event.get('event_link')
        calendar_event.location = event.get('location')
    else:
        # Update the event with event_id
        event = calendar_client.update_calendar_event(
            calendar_event.uid,
            calendar_event_data)
        print(event)
        new_event = False
        
        if not event.get('updated'):
            print("Event updation failed", event)
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
            calendar_event.event_id,
            calendar_event.webhook_uid,
            calendar_event.start_datetime)

        if not web_hook_response.get("success"):
            calendar_event.webhook_uid = None
    super(calendar_event.__class__, calendar_event).save()
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
    calendar_client = GoogleCalendar(self.event.created_by.calendar_auth)


    calendar_client.delete_calendar_event(calendar_event.uid)

    if calendar_event.webhook_uid:
        calendar_client.deactivate_webhook(
            calendar_event.webhook_uid,
            calendar_event.webhook_data["X-Goog-Resource-Id"]
            )
    return
