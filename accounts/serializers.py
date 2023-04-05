from django.utils import timezone
from rest_framework import serializers

from .models import Events, CalendarEvents


class EventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Events
        fields = "__all__"


class CalendarEventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvents
        fields = "__all__"

class BookingSerializer(serializers.Serializer):
    email = serializers.EmailField()
    start_datetime = serializers.JSONField()
    end_datetime = serializers.JSONField()

class SlotGenerationSerializer(serializers.Serializer):
    title = serializers.CharField()
    duration = serializers.IntegerField()
    slots = serializers.IntegerField()

    # def to_representation(self, instance):