from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Attendee, Event


class EventModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="123")
        self.event = Event.objects.create(
            owner=self.user,
            name="Django Conference",
            date=timezone.now(),
            capacity=2
        )

    def test_event_str(self):
        self.assertEqual(str(self.event), "Django Conference")

    def test_available_spots(self):
        self.assertEqual(self.event.available_spots(), 2)

        Attendee.objects.create(name="Alice", event=self.event)
        self.assertEqual(self.event.available_spots(), 1)

    def test_is_full(self):
        self.assertFalse(self.event.is_full())

        Attendee.objects.create(name="Alice", event=self.event)
        Attendee.objects.create(name="Bob", event=self.event)

        self.assertTrue(self.event.is_full())


class AttendeeModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="123")
        self.event = Event.objects.create(
            owner=self.user,
            name="Security Meetup",
            date=timezone.now(),
            capacity=10
        )

    def test_unique_attendee_per_event(self):
        Attendee.objects.create(name="Alice", event=self.event)

        with self.assertRaises(IntegrityError):
            Attendee.objects.create(name="Alice", event=self.event)


class EventViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="123")
        self.client.login(username="owner", password="123")
        self.event = Event.objects.create(
            owner=self.user,
            name="Blue Team Lab",
            date=timezone.now(),
            capacity=5
        )

    def test_event_list_view(self):
        response = self.client.get(reverse('event_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blue Team Lab")

    def test_create_event(self):
        response = self.client.post(reverse('create_event'), {
            'name': 'New Event',
            'date': '2026-01-01T12:00',
            'capacity': 10,
            'visibility': 'none',
        })

        self.assertEqual(Event.objects.count(), 2)
        self.assertRedirects(response, reverse('event_list'))

    def test_edit_event(self):
        response = self.client.post(
            reverse('edit_event', args=[self.event.id]),
            {
                'name': 'Updated Blue Team Lab',
                'date': '2026-05-01T10:00',
                'capacity': 8,
                'visibility': 'none',
            }
        )
        self.assertRedirects(response, reverse('event_detail', args=[self.event.id]))
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'Updated Blue Team Lab')
        self.assertEqual(self.event.capacity, 8)


class AttendeeRegistrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="123")
        self.client.login(username="owner", password="123")
        self.event = Event.objects.create(
            owner=self.user,
            name="AppSec Workshop",
            date=timezone.now(),
            capacity=1
        )

    def test_register_attendee_success(self):
        response = self.client.post(
            reverse('register_attendee', args=[self.event.id]),
            {'name': 'Alice', 'role': 'VIP'}
        )

        self.assertEqual(Attendee.objects.count(), 1)
        self.assertRedirects(
            response,
            reverse('event_detail', args=[self.event.id])
        )

    def test_cannot_register_when_event_is_full(self):
        Attendee.objects.create(name="Alice", event=self.event)

        self.client.post(
            reverse('register_attendee', args=[self.event.id]),
            {'name': 'Bob'}
        )

        self.assertEqual(Attendee.objects.count(), 1)

    def test_cannot_register_same_attendee_twice(self):
        self.client.post(
            reverse('register_attendee', args=[self.event.id]),
            {'name': 'Alice'}
        )

        self.client.post(
            reverse('register_attendee', args=[self.event.id]),
            {'name': 'Alice'}
        )

        self.assertEqual(Attendee.objects.count(), 1)

    def test_update_and_remove_attendee(self):
        attendee = Attendee.objects.create(name="Alice", role="guest", event=self.event)
        self.client.post(
            reverse('update_attendee_role', args=[self.event.id, attendee.id]),
            {'role': 'speaker'}
        )
        attendee.refresh_from_db()
        self.assertEqual(attendee.role, 'speaker')

        self.client.post(
            reverse('remove_attendee', args=[self.event.id, attendee.id])
        )
        self.assertEqual(Attendee.objects.count(), 0)


class DeleteEventSecurityTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="123")
        self.client.login(username="owner", password="123")
        self.event = Event.objects.create(
            owner=self.user,
            name="Critical Event",
            date=timezone.now(),
            capacity=10
        )

    def test_delete_event_get_not_allowed(self):
        response = self.client.get(
            reverse('delete_event', args=[self.event.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Event.objects.filter(id=self.event.id).exists())

    def test_non_owner_cannot_delete_event(self):
        other = User.objects.create_user(username="other", password="123")
        self.client.login(username="other", password="123")
        response = self.client.post(
            reverse('delete_event', args=[self.event.id])
        )
        self.assertTrue(Event.objects.filter(id=self.event.id).exists())


class EventOwnershipTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("u1", password="123")
        self.user2 = User.objects.create_user("u2", password="123")

        self.event = Event.objects.create(
            name="Private",
            owner=self.user1,
            date=timezone.now(),
            capacity=10
        )

    def test_user_cannot_see_others_event(self):
        self.client.login(username="u2", password="123")
        response = self.client.get("/")
        self.assertNotContains(response, "Private")


class GlobalAndInviteEventTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="123")
        self.guest = User.objects.create_user("guest", password="123")
        self.global_event = Event.objects.create(
            owner=self.owner,
            name="Global Summit",
            date=timezone.now(),
            capacity=5,
            is_global=True,
            invite_only=False,
        )
        self.invite_event = Event.objects.create(
            owner=self.owner,
            name="Secret Party",
            date=timezone.now(),
            capacity=5,
            is_global=False,
            invite_only=True,
        )

    def test_join_global_event(self):
        self.client.login(username="guest", password="123")
        response = self.client.post(reverse("join_event", args=[self.global_event.id]))
        self.assertRedirects(response, reverse("event_detail", args=[self.global_event.id]))
        self.assertTrue(
            Attendee.objects.filter(event=self.global_event, user=self.guest).exists()
        )

    def test_invite_checkin_flow(self):
        self.client.login(username="guest", password="123")
        response = self.client.post(
            reverse("invite_checkin", args=[self.invite_event.qr_token])
        )
        self.assertRedirects(response, reverse("event_detail", args=[self.invite_event.id]))
        self.assertIn(self.guest, self.invite_event.invited_users.all())
        self.assertTrue(
            Attendee.objects.filter(event=self.invite_event, user=self.guest).exists()
        )


class UserAuthTest(TestCase):
    def setUp(self):
        self.username = "test_user"
        self.password = "secure_pass123"
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_registration_view(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

        payload = {
            'username': 'new_guy',
            'password': 'password_high_123',
            'password2': 'password_high_123',
        }
        post_response = self.client.post(reverse('register'), payload)
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(User.objects.filter(username='new_guy').exists())

    def test_login_view(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

        login_data = {'username': self.username, 'password': self.password}
        post_response = self.client.post(reverse('login'), login_data)
        self.assertEqual(post_response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)


class ApiAndFilterViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="api_user", password="123")
        self.client.login(username="api_user", password="123")
        self.event = Event.objects.create(
            owner=self.user,
            name="Tech Meetup",
            date=timezone.now(),
            capacity=2,
            latitude=43.2389,
            longitude=76.8897,
            location_name="Almaty Hub",
        )

    def test_event_list_filters_and_sorting(self):
        response = self.client.get(reverse("event_list"), {
            "date_from": "2020-01-01",
            "date_to": "2030-12-31",
            "availability": "available",
            "sort_by": "name_asc",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tech Meetup")

    def test_profile_and_profile_events_api(self):
        prof_resp = self.client.get(reverse("profile"))
        self.assertEqual(prof_resp.status_code, 200)

        api_resp = self.client.get(reverse("api_profile_events"))
        self.assertEqual(api_resp.status_code, 200)
        data = api_resp.json()
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["name"], "Tech Meetup")

    def test_rest_api_crud(self):
        import json
        create_resp = self.client.post(
            reverse("api_create_event"),
            data=json.dumps({
                "name": "API Created Event",
                "date": "2026-12-01T15:00:00Z",
                "capacity": 20,
            }),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 200)
        event_id = create_resp.json()["event_id"]

        update_resp = self.client.put(
            reverse("api_update_event", args=[event_id]),
            data=json.dumps({"name": "API Updated Event", "capacity": 25}),
            content_type="application/json",
        )
        self.assertEqual(update_resp.status_code, 200)

        delete_resp = self.client.delete(
            reverse("api_delete_event", args=[event_id])
        )
        self.assertEqual(delete_resp.status_code, 200)
        self.assertFalse(Event.objects.filter(id=event_id).exists())
