
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from .forms import DesignCreateForm, DesignSettingsForm
from .models import SavedDesign, StyleOptions, StyleProfile, ColorPalette, RecommendedMotif

@login_required
def show_home(request):
    return render(request, "home_custom.html", {"selected_preference": request.session.get("fashion_preference", "")})

def fashion_preference(request):
    allowed_preferences = {"women", "men", "unisex"}
    if request.method == "POST":
        preference = request.POST.get("fashion_preference", "").strip().lower()
        if preference not in allowed_preferences:
            return redirect("batik_custom:fashion_preference")
        request.session["fashion_preference"] = preference
        request.session.pop("selected_style_id", None)
        request.session.pop("selected_palette_id", None)
        return redirect("batik_custom:style_quiz")
    return render(request, "fashion_preference.html", {"selected_preference": request.session.get("fashion_preference", "")})

def style_quiz(request):
    gender = request.session.get("fashion_preference", "").strip().lower()
    styles = StyleOptions.objects.filter(is_active=True).order_by("name", "id")
    if gender in {"women", "men"}:
        styles = styles.filter(gender__iexact=gender)
    elif gender == "unisex":
        styles = styles.filter(gender__iexact="unisex")
        unique_styles = []
        seen_names = set()
        for style in styles:
            normalized_name = style.name.strip().casefold()
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_styles.append(style)
        styles = unique_styles
    return render(request, "style_quiz.html", {"styles": styles, "selected_style": request.session.get("selected_style_id", "")})

def select_style(request):
    if request.method != "POST":
        return redirect("batik_custom:style_quiz")
    style_id = request.POST.get("style")
    gender = request.session.get("fashion_preference", "").strip().lower()
    styles = StyleOptions.objects.filter(is_active=True, id=style_id)
    if gender in {"women", "men", "unisex"}:
        styles = styles.filter(gender__iexact=gender)
    style = styles.first()
    if style is None:
        return redirect("batik_custom:style_quiz")
    request.session["selected_style_id"] = style.pk
    request.session.pop("selected_palette_id", None)
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
        request.session["selected_palette_id"] = palette.pk
        return redirect("batik_custom:recommended_motifs")
    return render(request, "explore_colors.html", {"palettes": palettes, "selected_palette": selected_palette})

@login_required
def custom_studio(request):
    motif_id = request.GET.get("motif")
    if not motif_id:
        return redirect("batik_custom:recommended_motifs")

    motif = get_object_or_404(RecommendedMotif, pk=motif_id, is_active=True)
    style_id = request.session.get("selected_style_id")
    palette_id = request.session.get("selected_palette_id")

    selected_style = StyleOptions.objects.filter(pk=style_id, is_active=True).first()
    selected_palette = ColorPalette.objects.filter(pk=palette_id, is_active=True).first()

    return render(request, "batik_custom/custom_studio.html", {
        "motif": motif,
        "selected_style": selected_style,
        "selected_palette": selected_palette,
    })


@login_required
def recommended_motifs(request):
    preference_raw = str(request.session.get("fashion_preference", "")).strip().upper()
    preference_map = {"WOMEN": "WOMEN", "WOMEN'S": "WOMEN", "MEN": "MEN", "MEN'S": "MEN", "UNISEX": "UNISEX", "SEMUA OUTFIT": "UNISEX", "ALL": "UNISEX"}
    preference = preference_map.get(preference_raw)
    style_id = request.session.get("selected_style_id")
    palette_id = request.session.get("selected_palette_id")
    if not preference:
        return redirect("batik_custom:fashion_preference")
    if not style_id:
        return redirect("batik_custom:style_quiz")
    if not palette_id:
        return redirect("batik_custom:explore_colors")
    motifs = RecommendedMotif.objects.filter(is_active=True, styles__id=style_id, palettes__id=palette_id, fashion_preference__name__iexact=preference).distinct().order_by("name")
    template = "batik_custom/partials/recommended_motifs.html" if request.headers.get("HX-Request") == "true" else "batik_custom/recommended_motifs.html"
    return render(request, template, {"motifs": motifs})

@login_required
def saved_design_list(request):
    designs = SavedDesign.objects.filter(user=request.user).select_related("motif", "palette")
    query = request.GET.get("q", "").strip()
    layout = request.GET.get("layout", "").strip()
    if query:
        designs = designs.filter(Q(title__icontains=query) | Q(motif__name__icontains=query) | Q(palette__name__icontains=query))
    valid_layouts = {choice[0] for choice in SavedDesign.LAYOUT_CHOICES}
    if layout in valid_layouts:
        designs = designs.filter(layout=layout)
    else:
        layout = ""
    context = {"designs": designs.order_by("-created_at"), "query": query, "selected_layout": layout}
    if request.headers.get("HX-Request") == "true":
        return render(request, "batik_custom/partials/design_results.html", context)
    return render(request, "batik_custom/saved_design_list.html", context)

@login_required
def saved_design_create(request):
    initial = {"motif": request.GET.get("motif"), "palette": request.session.get("selected_palette_id")}
    if request.method == "POST":
        form = DesignCreateForm(request.POST)
        if form.is_valid():
            design = form.save(commit=False)
            design.user = request.user
            design.save()
            if request.headers.get("HX-Request") == "true":
                return render(request, "batik_custom/partials/design_row.html", {"design": design})
            return redirect("batik_custom:saved_design_detail", pk=design.pk)
    else:
        form = DesignCreateForm(initial=initial)
    return render(request, "batik_custom/saved_design_form.html", {"form": form, "page_title": "Save Design"})

@login_required
def saved_design_detail(request, pk):
    design = get_object_or_404(SavedDesign.objects.select_related("motif", "palette"), pk=pk, user=request.user)
    return render(request, "batik_custom/saved_design_detail.html", {"design": design})

@login_required
def saved_design_update(request, pk):
    design = get_object_or_404(SavedDesign, pk=pk, user=request.user)
    if request.method == "POST":
        form = DesignSettingsForm(request.POST, instance=design)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request") == "true":
                return render(request, "batik_custom/partials/design_row.html", {"design": design})
            return redirect("batik_custom:saved_design_detail", pk=design.pk)
    else:
        form = DesignSettingsForm(instance=design)
    return render(request, "batik_custom/saved_design_form.html", {"form": form, "design": design, "page_title": "Edit Design"})

@login_required
@require_POST
def saved_design_delete(request, pk):
    design = get_object_or_404(SavedDesign, pk=pk, user=request.user)
    design.delete()
    if request.headers.get("HX-Request") == "true":
        designs = SavedDesign.objects.filter(user=request.user).select_related("motif", "palette")
        query = request.GET.get("q", "").strip()
        layout = request.GET.get("layout", "").strip()
        if query:
            designs = designs.filter(Q(title__icontains=query) | Q(motif__name__icontains=query) | Q(palette__name__icontains=query))
        valid_layouts = {choice[0] for choice in SavedDesign.LAYOUT_CHOICES}
        if layout in valid_layouts:
            designs = designs.filter(layout=layout)
        else:
            layout = ""
        return render(request, "batik_custom/partials/design_results.html", {"designs": designs.order_by("-created_at"), "query": query, "selected_layout": layout})
    return redirect("batik_custom:saved_design_list")
