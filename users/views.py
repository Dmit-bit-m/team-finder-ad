from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from utils import paginate_queryset
from .forms import ChangePasswordForm, EditProfileForm, LoginForm, RegisterForm
from .models import User


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            User.objects.create_user(
                email=form.cleaned_data['email'],
                name=form.cleaned_data['name'],
                surname=form.cleaned_data['surname'],
                password=form.cleaned_data['password'],
            )
            return redirect('users:login')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data['user'])
            return redirect('projects:list')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('projects:list')


def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    return render(request, 'users/user-details.html', {'user': user})


@login_required(login_url='/users/login/')
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:detail', user_id=request.user.id)
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, 'users/edit_profile.html', {'form': form, 'user': request.user})


@login_required(login_url='/users/login/')
def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.save()
            update_session_auth_hash(request, request.user)
            return redirect('users:detail', user_id=request.user.id)
    else:
        form = ChangePasswordForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})


def users_list(request):
    qs = User.objects.all().order_by('-id')
    page = paginate_queryset(qs, request)
    return render(request, 'users/participants.html', {
        'participants': page,
        'page_obj': page,
    })
