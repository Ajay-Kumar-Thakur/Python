# users/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, ProfileUpdateForm
from .models import Profile # Import the Profile model

def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account was created.')
            return redirect('profile')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('profile')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'users/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_view(request):
    # --- FIX: Use get_or_create to prevent crash ---
    # This will get the profile if it exists, or create a new one if it doesn't.
    # The new profile will use the default avatar set in your Profile model.
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Pass instance=profile to update the correct profile object
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Avatar updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
        
    return render(request, 'users/profile.html', {'form': form, 'profile': profile})