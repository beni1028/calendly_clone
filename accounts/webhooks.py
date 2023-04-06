from rest_framework.views import APIView
from rest_framework.response import Response

from scheduler.hook_authentication import Webhook

from accounts.models import CalendarEvents

@Webhook(url_path='accounts/webhook/event-update/<uid>/', lookup_field="uid")
class CalendarEventWebhookView(APIView):

    def post(self, request, uid):
        ''''
        1. Get the calender event from CalendarEvent Model
        2. If "X-Goog-Resource-State" == "sync"
            - Register the header
            - return
        3. Retrieve the event info using calendar client
        4. Check if event is Delete from calendar client response
            - CalendarEvent delete(cancelled=True) on instance
            - cancelled=True assurse no call made to google. 
        5. Store event info 
        '''
        try:
            calendar_event = CalendarEvents.objects.get(uid=uid)
            calendar_event.sync_calendar(headers=request.headers)
            return Response(status=200)

        except Exception as err:
            print(f"Error occured during Google Calendar Call Back: {err}")
            return Response(status=500)
