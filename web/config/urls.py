from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect

def index(request):
    return render(request, "index.html")

@login_required
def profile(request):
    return render(request, "profile.html")

@require_http_methods(["GET", "POST"])
def logout_any(request):
    logout(request)
    return redirect("/")

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre compte a été créé avec succès 🎉 Vous pouvez maintenant vous connecter.")
            return redirect("login")  # Redirige vers la page de connexion
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  # ✅ ajoute /login/ et /logout/
    path("profile/", profile, name="profile"),
    path("logout/", logout_any, name="logout_any"),
    path("signup/", signup, name="signup"), 
]
