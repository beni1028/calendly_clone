import requests

from django.shortcuts import get_object_or_404

from rest_framework import viewsets, views, response, status

from .models import Events, CalendarEvents
from .calendar import GoogleCalendar
from .serializers import EventsSerializer, CalendarEventsSerializer, BookingSerializer
from .tasks import update_slots


class EventsViewSet(viewsets.ModelViewSet):
    serializer_class = EventsSerializer
    queryset = Events.objects.all()


class GoogleCallBackView(views.APIView):

    def get(self, request):
        try:
            token_data = request.query_params.get('access_token', None)

        except KeyError as err:
            return response.Response({"message": err},
                                     status=status.HTTP_400_BAD_REQUEST)

        user_data = requests.get('https://www.googleapis.com/oauth2/v2/userinfo',
                                 params={'access_token': token_data})

        if user_data.status_code != 200:
            return response.Response(status=status.HTTP_400_BAD_REQUEST)


class BookingView(views.APIView):

    def post(self, request, slug):
        event = get_object_or_404(Events, slug=slug)
        serialzier = BookingSerializer(
            data=request.data,
            context={"invitees": event.invitees}
            )
        serialzier.is_valid(raise_exception=True)
        data = serialzier.validated_data

        # verify_avialiabilty
        # Also make sure that there are no overlapping events
        start_datetime = data["start_datetime"]
        end_datetime = data["end_datetime"]

        calendar_client = GoogleCalendar(event.created_by.calendar_auth)
        calendar_events = calendar_client.is_events_list(start_datetime, end_datetime)
        print(calendar_events)

        if not calendar_events["success"] or calendar_events["events"]:
            return response.Response("Please select a different slot,"
                                     "as this one is already booked.",status=status.HTTP_409_CONFLICT)

        # Check if email already has an calendar_event and trigger reschedule
        calendar_event = CalendarEvents.objects.filter(
            event=event,
            attendees__icontains=data["email"],
            deleted_at__isnull=True).last()

        if not calendar_event:
            add_slots_back = None
            CalendarEvents.objects.create(
                event=event,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                attendees=[event.created_by.email,
                           data['email']]
                )
        else:
            add_slots_back = {calendar_event.start_datetime.isoformat(): calendar_event.end_datetime.isoformat()}
            calendar_event.start_datetime = data["start_datetime"]
            calendar_event.end_datetime = data["end_datetime"]
            calendar_event.save()

        remove_slots = {start_datetime: end_datetime}
        print(remove_slots,"ttttttttttttttttttttttttttttttt")

        update_slots(slug, remove_slots, add_slots_back)

        return response.Response(
                                {"message": "Your slot was booked successfully"},
                                status=200
                                )

    def get(self, request, slug):
        event = get_object_or_404(Events, slug=slug)
        slots = event.get_available_slots()
        return response.Response({
            "title": event.title,
            "description": event.description,
            "duration": event.duration,
            "slots_to_display": slots
        })
