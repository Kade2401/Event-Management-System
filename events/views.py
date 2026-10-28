from datetime import datetime, time
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, F, Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from .forms import AttendeeForm, EventForm, RegisterForm
from .models import Attendee, Event
from .utils import is_global_manager


@login_required
def event_list(request):
    queryset = Event.objects.filter(
        Q(owner=request.user)
        | Q(invited_users=request.user)
        | Q(is_global=True, invite_only=False)
    ).filter(
        owner__isnull=False
    ).distinct()

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        try:
            date_from_dt = datetime.combine(
                datetime.fromisoformat(date_from).date(),
                time(0, 0, 0)
            )
            if timezone.is_naive(date_from_dt):
                date_from_dt = timezone.make_aware(date_from_dt)
            queryset = queryset.filter(date__gte=date_from_dt)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_datetime = datetime.combine(
                datetime.fromisoformat(date_to).date(),
                time(23, 59, 59)
            )
            if timezone.is_naive(date_to_datetime):
                date_to_datetime = timezone.make_aware(date_to_datetime)
            queryset = queryset.filter(date__lte=date_to_datetime)
        except ValueError:
            pass

    availability = request.GET.get('availability', 'all')

    if availability != 'all':
        queryset = queryset.annotate(
            attendees_count=Count('attendees', distinct=True)
        )

        if availability == 'available':
            queryset = queryset.filter(capacity__gt=F('attendees_count'))
        elif availability == 'full':
            queryset = queryset.filter(capacity__lte=F('attendees_count'))

    sort_by = request.GET.get('sort_by', 'date')

    if sort_by == 'date':
        queryset = queryset.order_by('-date')
    elif sort_by == 'date_asc':
        queryset = queryset.order_by('date')
    elif sort_by == 'name_asc':
        queryset = queryset.order_by('name')
    elif sort_by == 'name_desc':
        queryset = queryset.order_by('-name')

    context = {
        'events': queryset,
        'date_from': date_from,
        'date_to': date_to,
        'availability': availability,
        'sort_by': sort_by,
    }
    return render(request, 'events/event_list.html', context)


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.owner != request.user and not request.user.is_superuser:
        messages.error(request, "You can't delete this event.")
        return redirect("event_detail", event_id=event.id)

    if request.method == 'POST':
        event_name = event.name
        event.delete()
        messages.error(request, f"Event '{event_name}' has been deleted.")
        return redirect('event_list')
    return render(request, 'events/confirm_delete.html', {'event': event})


@login_required
def api_profile_events(request):
    qs = Event.objects.filter(
        Q(owner=request.user)
        | Q(invited_users=request.user)
        | Q(is_global=True, invite_only=False)
    ).distinct()

    data = []
    for e in qs:
        if e.latitude is None or e.longitude is None:
            continue

        data.append({
            "id": e.id,
            "name": e.name,
            "date": str(e.date),
            "location_name": e.location_name or "",
            "location_address": e.location_address or "",
            "lat": float(e.latitude),
            "lng": float(e.longitude),
            "url": f"/{e.id}/",  # если event_detail по /<id>/
            "is_global": bool(e.is_global),
        })

    return JsonResponse({"events": data})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id, owner__isnull=False)

    if event.invite_only:
        if not (
            request.user == event.owner
            or request.user in event.invited_users.all()
            or request.user.is_superuser
        ):
            return redirect("event_list")

    is_owner = (event.owner == request.user)
    is_invited = event.invited_users.filter(id=request.user.id).exists()
    is_public_global = (event.is_global and not event.invite_only)
    is_joined = event.attendees.filter(
        Q(user=request.user) | Q(name=request.user.username)
    ).exists()

    can_view = is_owner or is_invited or is_public_global or request.user.is_superuser
    if not can_view:
        return HttpResponseForbidden("You don't have access to this event.")

    attendees = event.attendees.all()
    is_full = attendees.count() >= event.capacity

    form = AttendeeForm() if is_owner else None

    invite_url = None
    can_see_invite = (event.invite_only and (is_owner or is_global_manager(request.user)))
    if can_see_invite:
        invite_url = request.build_absolute_uri(
            reverse("invite_checkin", args=[event.qr_token])
        )

    return render(request, "events/event_detail.html", {
        "event": event,
        "attendees": attendees,
        "is_full": is_full,
        "form": form,
        "invite_url": invite_url,
        "can_see_invite": can_see_invite,
        "is_owner": is_owner,
        "is_invited": is_invited,
        "is_joined": is_joined,
    })


@login_required
def create_event(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES or None, user=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.owner = request.user

            visibility = form.cleaned_data.get("visibility") or "none"

            if visibility == "global":
                if not is_global_manager(request.user):
                    messages.error(request, "Only globals group can create global events.")
                    return redirect("event_list")
                event.is_global = True
                event.invite_only = False
            elif visibility == "invite":
                event.is_global = False
                event.invite_only = True
            else:
                event.is_global = False
                event.invite_only = False

            event.save()
            form.save_m2m()
            messages.success(request, "Event created!")
            return redirect("event_list")

        messages.error(request, f"Form errors: {form.errors}")
    else:
        form = EventForm(user=request.user)

    return render(request, "events/create_event.html", {"form": form})


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.owner != request.user:
        messages.error(request, "You can't edit this event.")
        return redirect("event_detail", event_id=event.id)

    if request.method == "POST":
        form = EventForm(request.POST or None, instance=event, user=request.user)
        if form.is_valid():
            new_capacity = form.cleaned_data["capacity"]
            if new_capacity < event.attendees.count():
                messages.error(
                    request,
                    f"Cannot reduce capacity below current number of attendees ({event.attendees.count()})."
                )
                return render(request, "events/edit_event.html", {"form": form, "event": event})

            visibility = form.cleaned_data.get("visibility") or "none"

            if visibility == "global" and not is_global_manager(request.user):
                messages.error(request, "Only globals group can create global events.")
                return redirect("event_list")

            updated_event = form.save(commit=False)

            if visibility == "global":
                updated_event.is_global = True
                updated_event.invite_only = False
            elif visibility == "invite":
                updated_event.is_global = False
                updated_event.invite_only = True
            else:
                updated_event.is_global = False
                updated_event.invite_only = False

            updated_event.save()
            form.save_m2m()

            messages.success(request, "Event updated!")
            return redirect("event_detail", event_id=updated_event.id)
    else:
        form = EventForm(instance=event, user=request.user)

    return render(request, "events/edit_event.html", {"form": form, "event": event})


@login_required
def register_attendee(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.owner != request.user:
        messages.error(request, "You can't register attendee for this event.")
        return redirect("event_detail", event_id=event.id)

    if request.method == 'POST':
        form = AttendeeForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            role = form.cleaned_data.get('role', '').strip()

            if event.is_full():
                messages.error(request, "Cannot register. Event is full!")
            elif Attendee.objects.filter(name=name, event=event).exists():
                messages.warning(request, f"{name} is already registered.")
            else:
                Attendee.objects.create(
                    name=name,
                    role=role,
                    event=event
                )
                messages.info(request, f"{name} successfully registered!")
    return redirect('event_detail', event_id=event.id)


@login_required
def update_attendee_role(request, event_id, attendee_id):
    event = get_object_or_404(Event, id=event_id, owner=request.user)
    attendee = get_object_or_404(Attendee, id=attendee_id, event=event)

    if event.owner != request.user:
        messages.error(request, "You can't edit attendee for this event.")
        return redirect("event_detail", event_id=event.id)

    if request.method == "POST":
        new_role = request.POST.get("role", "").strip()
        attendee.role = new_role
        attendee.save()
        messages.success(request, f"Role updated for {attendee.name}")

    return redirect("event_detail", event_id=event.id)


@login_required
def remove_attendee(request, event_id, attendee_id):
    event = get_object_or_404(Event, id=event_id, owner=request.user)
    attendee = get_object_or_404(Attendee, id=attendee_id, event=event)

    if event.owner != request.user:
        messages.error(request, "You can't delete attendee for this event.")
        return redirect("event_detail", event_id=event.id)

    if request.method == "POST":
        attendee.delete()
        messages.success(request, "Attendee removed")

    return redirect("event_detail", event_id=event.id)


def api_event_list(request):
    if request.method == 'GET':
        events = Event.objects.all().values(
            'id', 'name', 'date', 'capacity'
        )
        return JsonResponse(list(events), safe=False)


@csrf_exempt
def api_create_event(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        owner = request.user if request.user.is_authenticated else User.objects.first()
        if owner is None:
            owner = User.objects.create_user(username="api_default_owner")
        event = Event.objects.create(
            owner=owner,
            name=data['name'],
            date=data['date'],
            capacity=data['capacity']
        )
        return JsonResponse({
            'status': 'created',
            'event_id': event.id
        })


@csrf_exempt
def api_update_event(request, event_id):
    if request.method == "PUT":
        body = json.loads(request.body)
        event = get_object_or_404(Event, id=event_id)

        event.name = body.get("name", event.name)
        event.date = body.get("date", event.date)
        event.capacity = body.get("capacity", event.capacity)

        event.save()
        return JsonResponse({"status": "updated"})


@csrf_exempt
def api_delete_event(request, event_id):
    if request.method == "DELETE":
        event = get_object_or_404(Event, id=event_id)
        event.delete()
        return JsonResponse({"status": "deleted"})


def register(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        password2 = request.POST.get('password2', password)

        if not username or not password:
            messages.error(request, 'Username and password are required')
            return render(request, 'registration/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Login taken')
            return render(request, 'registration/register.html')

        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'registration/register.html')

        User.objects.create_user(username=username, password=password)
        messages.success(request, 'Account created!')
        return redirect('login')

    return render(request, 'registration/register.html')


def user_login(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)

        if user:
            login(request, user)
            return redirect('profile')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'registration/login.html')
    return render(request, 'registration/login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()

        messages.success(request, 'Account deleted')
        return redirect('register')
    return redirect('profile')


@login_required
def profile(request):
    user = request.user
    events = []
    context = {
        'user': user,
        'events': events
    }
    return render(request, 'events/profile.html', context)


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.GET.get('search'):
            queryset = queryset.filter(name__icontains=self.request.GET['search'].strip())
        if self.request.GET.get('future_only'):
            queryset = queryset.filter(date__gte=timezone.now())
        return queryset.order_by('date')


@login_required
def invite_checkin(request, token):
    event = get_object_or_404(Event, qr_token=token, invite_only=True)
    already_attending = event.attendees.filter(
        Q(user=request.user) | Q(name=request.user.username)
    ).exists()

    if event.is_full() and not already_attending:
        messages.error(request, "Event is full.")
        return redirect("event_list")

    if request.method == "POST":
        event.invited_users.add(request.user)

        existing = event.attendees.filter(
            Q(user=request.user) | Q(name=request.user.username)
        ).first()
        if existing:
            if existing.user is None:
                existing.user = request.user
                existing.save(update_fields=["user"])
        else:
            Attendee.objects.create(
                event=event,
                user=request.user,
                name=request.user.username,
                role="invited"
            )

        messages.success(request, "Invitation accepted! Event added to your list.")
        return redirect("event_detail", event_id=event.id)

    return render(request, "events/invite_checkin.html", {
        "event": event,
        "is_full": event.is_full(),
    })


@login_required
def join_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_global=True, invite_only=False)

    if request.method != "POST":
        return redirect("event_detail", event_id=event.id)

    existing = event.attendees.filter(
        Q(user=request.user) | Q(name=request.user.username)
    ).first()
    if existing:
        if existing.user is None:
            existing.user = request.user
            existing.save(update_fields=["user"])
        messages.success(request, "You are registered for this global event!")
        return redirect("event_detail", event_id=event.id)

    if event.is_full():
        messages.error(request, "Event is full!")
        return redirect("event_detail", event_id=event.id)

    Attendee.objects.create(
        event=event,
        user=request.user,
        name=request.user.username,
        role="guest"
    )

    messages.success(request, "You are registered for this global event!")
    return redirect("event_detail", event_id=event.id)


@receiver(pre_delete, sender=Event)
def cleanup_event(sender, instance, **kwargs):
    instance.invited_users.clear()
