from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Event, Attendee


class EventForm(forms.ModelForm):
    VISIBILITY_CHOICES = [
        ("none", "Normal"),
        ("invite", "Private (invite-only)"),
        ("global", "Global"),
    ]

    visibility = forms.ChoiceField(
        choices=VISIBILITY_CHOICES,
        widget=forms.RadioSelect,
        required=False,
        initial="none",
        label="Event type",
    )

    class Meta:
        model = Event
        fields = [
            "name", "description", "date", "capacity",
            "location_name", "location_address",
            "latitude", "longitude",
        ]
        widgets = {
            'date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Event description (optional)"
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        if user and (not user.is_superuser) and (not user.groups.filter(name="globals").exists()):
            self.fields["visibility"].choices = [
                (v, label) for (v, label) in self.fields["visibility"].choices
                if v != "global"
            ]

        if instance:
            if getattr(instance, "is_global", False):
                self.fields["visibility"].initial = "global"
            elif getattr(instance, "invite_only", False):
                self.fields["visibility"].initial = "invite"
            else:
                self.fields["visibility"].initial = "none"


class AttendeeForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['name', 'role']
        widgets = {
            'role': forms.TextInput(attrs={
                'placeholder': 'Example: guest / speaker / VIP',
                'class': 'form-control'
            })
        }


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")


class AttendeeRoleForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['role']
        widgets = {
            'role': forms.TextInput(attrs={
                'placeholder': 'New role',
                'class': 'form-control'
            })
        }
