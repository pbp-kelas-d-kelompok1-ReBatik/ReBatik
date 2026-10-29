from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BatikMotifForm
from .models import BatikMotif

def show_home(request):
    return render(request, "home.html")

def show_batik_story(request):
    # Semua pencarian, filter, dan pengurutan dilakukan oleh QuerySet Django
    # sehingga data diproses di database, bukan hanya menyembunyikan kartu via JavaScript.
    batiks = BatikMotif.objects.all()

    query = request.GET.get("q", "").strip()
    asal = request.GET.get("asal", "").strip()
    sort = request.GET.get("sort", "nama_asc").strip()

    if query:
        from django.db.models import Q
        batiks = batiks.filter(
            Q(nama__icontains=query)
            | Q(asal__icontains=query)
            | Q(filosofi__icontains=query)
            | Q(deskripsi__icontains=query)
        )

    valid_asal = {choice[0] for choice in BatikMotif.ASAL_CHOICES}
    if asal and asal in valid_asal:
        batiks = batiks.filter(asal=asal)
    else:
        asal = ""

    if sort == "nama_desc":
        batiks = batiks.order_by("-nama", "id_story")
    else:
        sort = "nama_asc"
        batiks = batiks.order_by("nama", "id_story")

    batiks = batiks.annotate(favorite_count=Count("favorited_by", distinct=True))
    if request.user.is_authenticated:
        batiks = batiks.annotate(
            is_favorited=Exists(
                BatikMotif.objects.filter(pk=OuterRef("pk"), favorited_by=request.user)
            )
        )
    else:
        batiks = batiks.annotate(is_favorited=Exists(BatikMotif.objects.none()))

    context = {
        "judul": "Batik Story",
        "ket1": (
            "Jelajahi kisah di balik batik Indonesia. Kenali sejarah, "
            "filosofi, dan makna dari berbagai motif batik Nusantara."
        ),
        "batiks": batiks,
        "query": query,
        "selected_asal": asal,
        "asal_choices": BatikMotif.ASAL_CHOICES,
        "selected_sort": sort,
    }
    return render(request, "batik_story.html", context)

@login_required
@require_POST
def toggle_favorite(request, id_story):
    batik = get_object_or_404(BatikMotif, id_story=id_story)
    if batik.favorited_by.filter(pk=request.user.pk).exists():
        batik.favorited_by.remove(request.user)
        is_favorited = False
    else:
        batik.favorited_by.add(request.user)
        is_favorited = True
    return JsonResponse({"success": True, "is_favorited": is_favorited, "favorite_count": batik.favorited_by.count()})

@login_required
def add_batik(request):
    if not request.user.is_staff:
        raise PermissionDenied
    if request.method == "POST":
        form = BatikMotifForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Motif batik berhasil ditambahkan!")
            return redirect("batik_story:show_batik_story")
    else:
        form = BatikMotifForm()
    return render(request, "add_batik.html", {"form": form})

@login_required
@require_POST
def delete_story(request, id_story):
    if not request.user.is_staff:
        raise PermissionDenied
    story = get_object_or_404(BatikMotif, id_story=id_story)
    story.delete()
    messages.success(request, "Cerita batik berhasil dihapus!")
    return redirect("batik_story:show_batik_story")

def story_detail(request, id_story):
    story = get_object_or_404(BatikMotif, id_story=id_story)
    return render(request, "story_detail.html", {"story": story})

@login_required
def story_edit(request, id_story):
    if not request.user.is_staff:
        raise PermissionDenied
    batik = get_object_or_404(BatikMotif, id_story=id_story)
    if request.method == "POST":
        form = BatikMotifForm(request.POST, request.FILES, instance=batik)
        if form.is_valid():
            form.save()
            messages.success(request, "YEAYY BERHASIL DI EDIT")
            return redirect("batik_story:show_batik_story")
    else:
        form = BatikMotifForm(instance=batik)
    return render(request, "story_edit.html", {"form": form, "batik": batik})