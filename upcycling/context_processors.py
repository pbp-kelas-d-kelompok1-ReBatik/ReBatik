from .models import ArtisanProfile


def upcycling_navigation(request):
    user = request.user
    can_open_artisan_dashboard = (
        user.is_authenticated
        and user.groups.filter(name="Artisan").exists()
        and ArtisanProfile.objects.filter(user=user).exists()
    )
    return {"can_open_artisan_dashboard": can_open_artisan_dashboard}
