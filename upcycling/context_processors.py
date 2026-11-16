from .models import ArtisanProfile


def upcycling_navigation(request):
    """Expose whether the signed-in user has the artisan role and profile."""
    user = request.user
    can_open_artisan_dashboard = (
        user.is_authenticated
        and user.groups.filter(name="Artisan").exists()
        and ArtisanProfile.objects.filter(user=user).exists()
    )
    return {"can_open_artisan_dashboard": can_open_artisan_dashboard}
