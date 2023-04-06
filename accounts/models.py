import binascii
import os
import re
import random, string

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

from django_celery_beat.models import PeriodicTask


class MyAccountManager(BaseUserManager):
    '''
    Extending the BaseUserManager.
    '''
    def create_user(self, email, password=None):
        '''
        OverWriting the create_user function.
        '''
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        '''
        OverWriting the create_superuser function.
        '''

        user = self.create_user(
            email=self.normalize_email(email),
            password=password,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    '''
    Creating thr custom user module schema.
    '''
    email                   = models.EmailField(verbose_name="email", max_length=60, unique=True)
    date_joined             = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login              = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin                = models.BooleanField(default=False)
    is_active               = models.BooleanField(default=True)
    is_staff                = models.BooleanField(default=False)
    is_superuser            = models.BooleanField(default=False)
    first_name              = models.CharField(max_length=15, blank=True, null=True)
    last_name               = models.CharField(max_length=15, blank=True, null=True)
    calendar_auth           = models.JSONField(null=True, blank=True)

    USERNAME_FIELD = 'email'

    objects = MyAccountManager()

    def __str__(self):
        '''
        Return the username as string
        '''
        return self.email

    def has_perm(self, perm, obj=None):
        '''
        For checking permissions. to keep it simple all admin have ALL permissons.
        '''
        return self.is_admin

    def has_module_perms(self, app_label):
        '''
        # Does this user have permission to view this app? (ALWAYS YES FOR SIMPLICITY)
        '''
        return True


class WebhookToken(models.Model):
    key             = models.CharField(max_length=40, primary_key=True)
    url             = models.URLField()
    created         = models.DateTimeField(auto_now_add=True)
    name            = models.CharField(max_length=50)
    lookup_field    = models.CharField(max_length=50, default="", blank=True, null=True)

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        from django.urls import reverse
        if not self.key:
            self.key = self.generate_key()
            print(self.lookup_field, self.name)
            # self.url = reverse(self.name, args=["13456"])
        return super().save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()


class Events(models.Model):

    title           = models.CharField(max_length=250)
    description     = models.TextField(blank=True, null=True)
    duration        = models.IntegerField()
    slug            = models.SlugField(unique=True)
    location        = models.URLField(blank=True, null=True)

    invitees        = models.JSONField(null=True, blank=True)
    reminders       = models.JSONField(null=True, blank=True) # {"email":[5,10,15,20]}
    availabilty     = models.JSONField()  #{start_dt: end_dt}
    slots           = models.JSONField(null=True, blank=True)

    created_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    deleted_at      = models.DateTimeField(blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title

    def generate_slug(self):
        random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.slug = slugify(f"{self.title}-{random_string}")

    def save(self, *args, **kwargs):
        if self.pk:
            old_obj = self.__class__.objects.get(id=self.pk)
        else:
            old_obj = False
        if not old_obj:
            self.generate_slug()
            self._create_slots()

        super().save(*args, **kwargs)
        return

    def _convert_datetime_to_slots(self, availability):
        slots = {}
        for start_time, end_time in availability.items():
            duration = timezone.timedelta(minutes=self.duration)
            slot_end_time = start_time
            while slot_end_time + duration <= end_time:
                slot_start_time = slot_end_time 
                slot_end_time = slot_start_time + duration
                slots[slot_start_time] = slot_end_time
        return slots

    def _convert_to_datetime_dict(self):
        availabilty = {
            timezone.datetime.fromisoformat(k):
            timezone.datetime.fromisoformat(v)
            for k, v in self.availabilty.items()
                       }
        return availabilty

    def _convert_to_iso_datetime_dict(self, slots):
        slots = {
            k.isoformat(): v.isoformat()
            for k, v in slots.items()
                       }
        return slots

    def _create_slots(self):
        availabilty = self._convert_to_datetime_dict()
        slots = self._convert_datetime_to_slots(availabilty)
        self.slots = self._convert_to_iso_datetime_dict(slots)
        super().save()

    def get_available_slots(self, *args, **kwargs):
        '''
        Get slots from event model and check about availability
        '''
        slots = self.slots
        now = timezone.now() + timezone.timedelta(minutes=60)
        
        # remove old slots by date
        slots = dict(
            (start_datetime, end_datetime)
            for start_datetime, end_datetime in slots.items()
            if timezone.datetime.fromisoformat(start_datetime)
            > now
        )

        if self.slots != slots:
            self.slots = slots
            super().save()

        return slots

class CalendarEvents(models.Model):
    event               = models.ForeignKey(Events, on_delete=models.SET_NULL, null=True, related_name="scheduled_events")
    tasks               = models.ManyToManyField(PeriodicTask, blank=True)

    uid                 = models.CharField(max_length=26, null=True, blank=True)
    location            = models.CharField(max_length=200, blank=True, null=True)
    attendees           = models.JSONField(blank=True, null=True)

    start_datetime      = models.DateTimeField()
    end_datetime        = models.DateTimeField()
    timezone            = models.CharField(max_length=20, default='Asia/Kolkata')

    calendar_response_data = models.JSONField(blank=True, null=True)
    
    deleted_at      = models.DateTimeField(blank=True, null=True)
    webhook_uid         = models.CharField(max_length=40, blank=True, null=True, unique=True)
    webhook_data        = models.JSONField(blank=True, null=True)

    def __str__(self):
        return str(self.id) 

    def save(self, call_super=False, *args, **kwargs):
        if call_super:
            super().save()
            return

        from accounts.tasks import create_calender_event
        super().save(*args, **kwargs)
        print("here")
        create_calender_event.delay(self.id)

    def delete(self, *args, **kwargs):
        # disable all the associated tasks (reminders/follow-ups)
        self.tasks.filter(enabled=True).update(enabled=False)

        from .tasks import delete_event_from_calendar
        delete_event_from_calendar(self.id)
        self.deleted_at = timezone.now()
        super().save()


    def generate_webhook_uid(self):
        timestamp = str(int(timezone.now().timestamp()))
        random_string = ''.join(random.choices(
            string.ascii_letters + string.digits,
            k=40-len(timestamp)))
        self.webhook_uid = str(timestamp + random_string)

    def sync_calendar(self, **kwargs):
        from .calendar import GoogleCalendar
        headers = kwargs.get("headers")
        if headers.get("X-Goog-Resource-State") == "sync":
            self.webhook_data = {**headers}
            super().save()
            return

        calendar_client = GoogleCalendar(self.event.created_by.calendar_auth)
        event = calendar_client.retrieve_calendar_event(self.uid)
        self.calendar_response_data = event
        if event.get("status") == 'cancelled':
            self.delete()
        return
