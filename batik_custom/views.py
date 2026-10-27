from django.shortcuts import render, redirect
from .models import StyleOptions, StyleProfile, ColorPalette


def show_home(request):
    return render(
        request,
        "fashion_preference.html",
        {
            "selected_preference": request.session.get(
                "fashion_preference", ""
            )
        },
    )


def fashion_preference(request):
    allowed_preferences = {"women", "men"}
    if request.method == "POST":
        preference = request.POST.get("fashion_preference", "")
        if preference not in allowed_preferences:
            return redirect("batik_custom:fashion_preference")
        request.session["fashion_preference"] = preference
        return redirect("batik_custom:style_quiz")

    return render(
        request,
        "fashion_preference.html",
        {
            "selected_preference": request.session.get(
                "fashion_preference", ""
            )
        },
    )


def style_quiz(request):
    gender = request.session.get("fashion_preference")
    styles = StyleOptions.objects.filter(is_active=True)
    if gender in {"women", "men"}:
        styles = styles.filter(gender=gender)
    return render(request, "style_quiz.html", {"styles": styles})


def select_style(request):
    if request.method != "POST":
        return redirect("batik_custom:style_quiz")

    style_id = request.POST.get("style")
    gender = request.session.get("fashion_preference")

    styles = StyleOptions.objects.filter(id=style_id, is_active=True)

    if gender in {"women", "men"}:
        styles = styles.filter(gender=gender)

    if not styles.exists():
        return redirect("batik_custom:style_quiz")

    request.session["selected_style_id"] = int(style_id)
    return redirect("batik_custom:style_quiz")

def custom_studio(request):
    return render(request, "batik_custom/custom_studio.html")
