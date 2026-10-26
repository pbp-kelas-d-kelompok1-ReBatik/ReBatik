
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StyleOptions, StyleProfile, ColorPalette

@login_required
def show_home(request):
    return render(request, "home_custom.html", {"selected_preference": request.session.get("fashion_preference", "")})

def fashion_preference(request):
    allowed_preferences = {"women", "men"}
    if request.method == "POST":
        preference = request.POST.get("fashion_preference", "")
        if preference not in allowed_preferences:
            return redirect("batik_custom:fashion_preference")
        request.session["fashion_preference"] = preference
        return redirect("batik_custom:style_quiz")
    return render(request, "fashion_preference.html", {"selected_preference": request.session.get("fashion_preference", "")})

def style_quiz(request):
    gender = request.session.get("fashion_preference")
    styles = StyleOptions.objects.filter(is_active=True)
    if gender in {"women", "men"}:
        styles = styles.filter(gender=gender)
    return render(request, "style_quiz.html", {"styles": styles, "selected_style": request.session.get("selected_style_id", "")})

def select_style(request):
    if request.method != "POST":
        return redirect("batik_custom:style_quiz")
    style_id = request.POST.get("style")
    gender = request.session.get("fashion_preference")
    styles = StyleOptions.objects.filter(id=style_id, is_active=True)
    if gender in {"women", "men"}:
        styles = styles.filter(gender=gender)
    style = styles.first()
    if style is None:
        return redirect("batik_custom:style_quiz")
    request.session["selected_style_id"] = style.id
    return redirect("batik_custom:explore_colors")

@login_required
def explore_colors(request):
    palettes = ColorPalette.objects.filter(is_active=True)
    selected_palette = request.session.get("selected_palette_id", "")
    if request.method == "POST":
        palette_id = request.POST.get("palette")
        palette = palettes.filter(id=palette_id).first()
        if palette is None:
            return render(request, "explore_colors.html", {"palettes": palettes, "selected_palette": palette_id or ""})
        request.session["selected_palette_id"] = palette.id
        return redirect("batik_custom:custom_studio")
    return render(request, "explore_colors.html", {"palettes": palettes, "selected_palette": selected_palette})

@login_required
def custom_studio(request):
    return render(request, "batik_custom/custom_studio.html")
