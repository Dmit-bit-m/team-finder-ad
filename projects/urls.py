from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
    path('list/', views.project_list, name='list'),
    path('create-project/', views.create_project, name='create'),
    path('skills/', views.skills_autocomplete, name='skills-autocomplete'),
    path('<int:project_id>/', views.project_detail, name='detail'),
    path('<int:project_id>/edit/', views.edit_project, name='edit'),
    path('<int:project_id>/complete/', views.complete_project, name='complete'),
    path(
        '<int:project_id>/toggle-participate/',
        views.toggle_participate,
        name='toggle-participate',
    ),
    path('<int:project_id>/skills/add/', views.add_skill, name='add-skill'),
    path('<int:project_id>/skills/<int:skill_id>/remove/', views.remove_skill, name='remove-skill'),
]
