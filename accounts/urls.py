from django.urls import path, include, reverse
from rest_framework.routers import DefaultRouter

from .views import *
from .webhooks import CalendarEventWebhookView

router = DefaultRouter()
router.register(r'events/(?P<slug>[^/.]+)', EventsViewSet, basename='events')
# router.register(r'calendar-events', CalendarEventViewSet, basename='calendar-events')

app_name = "accounts"

urlpatterns = [
    path('oauth2callback/', views.GoogleAuthCallbackView.as_view(), name='google-auth-callback'),
    path("event-slots/<slug>/", BookingView.as_view(), name="event-slots"),
    path('webhook/event-update/<uid>/', CalendarEventWebhookView.as_view(), name=CalendarEventWebhookView.__name__.lower()),
    path("", include(router.urls)),
]
