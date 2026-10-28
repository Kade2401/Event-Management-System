from django.contrib import admin
from .models import Event, Attendee


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'capacity')
    search_fields = ('name',)
    list_filter = ('date',)


@admin.register(Attendee)
class AttendeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'event')
    search_fields = ('name',)
    list_filter = ('event',)
