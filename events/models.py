from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import uuid


class Event(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events'
    )

    invited_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="invited_events"
    )

    name = models.CharField(max_length=200)
    date = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    location_name = models.CharField(max_length=200, blank=True)
    location_address = models.CharField(max_length=300, blank=True)
    latitude = models.DecimalField(max_digits=13, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=13, decimal_places=10, null=True, blank=True)
    description = models.TextField(blank=True)

    is_global = models.BooleanField(default=False)

    invite_only = models.BooleanField(default=False)

    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return self.name

    def available_spots(self):
        return self.capacity - self.attendees.count()

    def is_full(self):
        return self.attendees.count() >= self.capacity


class Attendee(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50, blank=True)
    event = models.ForeignKey(
        Event,
        related_name='attendees',
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            # один пользователь — один раз на ивент
            models.UniqueConstraint(
                fields=["event", "user"],
                name="unique_user_per_event"
            ),
            # защита от дублей по имени (как у тебя было)
            models.UniqueConstraint(
                fields=["event", "name"],
                name="unique_name_per_event"
            ),
        ]

    def __str__(self):
        if self.user:
            return f"{self.user.username} ({self.role}) — {self.event.name}"
        return f"{self.name} ({self.role}) — {self.event.name}"
