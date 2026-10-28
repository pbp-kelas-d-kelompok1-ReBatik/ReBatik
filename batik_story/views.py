from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .forms import BatikMotifForm
from .models import BatikMotif

def show_home(request):
    return render(request, "home.html")

def show_batik_story(request):
    context = {
        "judul": "Batik Story",
        "ket1": "Jelajahi kisah di balik batik Indonesia. Kenali sejarah, filosofi, dan makna dari berbagai motif batik Nusantara.",
        "batiks": BatikMotif.objects.all(),
    }
    return render(request, "batik_story.html", context)

@login_required
def add_story(request):
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
    return render(request, "add_story.html", {"form": form})

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
    return render(request, "batik_story/story_detail.html", {"story": story})

@login_required
def story_edit(request, id_story):
    if not request.user.is_staff:
        raise PermissionDenied
    story = get_object_or_404(BatikMotif, id_story=id_story)
    if request.method == "POST":
        form = BatikMotifForm(request.POST,request.FILES,instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, "Cerita batik berhasil diperbarui!")
            return redirect("batik_story:show_batik_story")
    else:
        form = BatikMotifForm(instance=story)
    return render(request, "story_edit.html",{"form": form, "story": story} )