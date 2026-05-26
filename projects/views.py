import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from utils import AUTOCOMPLETE_LIMIT, paginate_queryset
from .forms import ProjectForm
from .models import Project, Skill


def project_list(request):
    projects = Project.objects.all().select_related('owner').order_by('-created_at')
    all_skills = Skill.objects.values_list('name', flat=True).order_by('name')
    active_skill = request.GET.get('skill', '')

    if active_skill:
        projects = projects.filter(skills__name=active_skill)

    page = paginate_queryset(projects, request.GET.get('page', 1))

    return render(request, 'projects/project_list.html', {
        'projects': page,
        'all_skills': all_skills,
        'active_skill': active_skill,
        'page_obj': page,
    })


def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return render(request, 'projects/project-details.html', {'project': project})


@login_required(login_url='/users/login/')
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            project.participants.add(request.user)
            return redirect(f'/projects/{project.id}/')
    else:
        form = ProjectForm()
    return render(request, 'projects/create-project.html', {'form': form, 'is_edit': False})


@login_required(login_url='/users/login/')
def edit_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect(f'/projects/{project.id}/')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/create-project.html', {'form': form, 'is_edit': True})


@login_required(login_url='/users/login/')
@require_POST
def complete_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if project.owner != request.user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if project.status != 'open':
        return JsonResponse({'status': 'error', 'message': 'Already closed'}, status=400)
    project.status = 'closed'
    project.save()
    return JsonResponse({'status': 'ok', 'project_status': 'closed'})


@login_required(login_url='/users/login/')
@require_POST
def toggle_participate(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    user = request.user
    if user in project.participants.all():
        project.participants.remove(user)
        return JsonResponse({'status': 'ok', 'participant': False})
    project.participants.add(user)
    return JsonResponse({'status': 'ok', 'participant': True})


def skills_autocomplete(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)
    skills = Skill.objects.filter(name__istartswith=q).order_by('name')[:AUTOCOMPLETE_LIMIT]
    return JsonResponse(list(skills.values('id', 'name')), safe=False)


@login_required(login_url='/users/login/')
@require_POST
def add_skill(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if project.owner != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    skill_id = body.get('skill_id')
    name = body.get('name', '').strip()

    if skill_id:
        skill = get_object_or_404(Skill, pk=skill_id)
        created = False
    elif name:
        skill, created = Skill.objects.get_or_create(name=name)
    else:
        return JsonResponse({'error': 'skill_id or name required'}, status=400)

    added = skill not in project.skills.all()
    if added:
        project.skills.add(skill)

    return JsonResponse({
        'skill_id': skill.id,
        'id': skill.id,
        'name': skill.name,
        'created': created,
        'added': added,
    })


@login_required(login_url='/users/login/')
@require_POST
def remove_skill(request, project_id, skill_id):
    project = get_object_or_404(Project, pk=project_id)
    if project.owner != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    skill = get_object_or_404(Skill, pk=skill_id)
    if skill not in project.skills.all():
        return JsonResponse({'error': 'Skill not in project'}, status=400)
    project.skills.remove(skill)
    return JsonResponse({'status': 'ok'})
