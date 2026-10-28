from django.urls import path
from . import views

urlpatterns = [
    path(
        '<int:event_id>/attendee/<int:attendee_id>/update-role/',
        views.update_attendee_role,
        name='update_attendee_role'
    ),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('profile/', views.profile, name='profile'),
    path('', views.event_list, name='event_list'),
    path('events/', views.event_list),
    path('create/', views.create_event, name='create_event'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/', views.event_detail),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('<int:event_id>/register/', views.register_attendee, name='register_attendee'),
    path('<int:event_id>/remove/<int:attendee_id>/', views.remove_attendee, name='remove_attendee'),
    path('api/events/', views.api_event_list, name='api_event_list'),
    path('api/events/create/', views.api_create_event, name='api_create_event'),
    path('api/events/<int:event_id>/', views.api_update_event, name='api_update_event'),
    path('api/events/<int:event_id>/delete/', views.api_delete_event, name='api_delete_event'),
    path('invite/<uuid:token>/', views.invite_checkin, name='invite_checkin'),
    path('events/<int:event_id>/join/', views.join_event, name='join_event'),
    path('api/profile-events/', views.api_profile_events, name='api_profile_events'),
]
