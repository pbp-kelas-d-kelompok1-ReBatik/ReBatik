from rest_framework.permissions import SAFE_METHODS, BasePermission

from .views import is_artisan_or_staff


class IsArtisanStaffOrReadOnly(BasePermission):
    """Semua pengunjung boleh membaca katalog; hanya Artisan/Admin/staff yang
    boleh menambah, mengubah, atau menyembunyikan produk.

    Aturan yang sama dengan view web ``manage_product_*`` (``staff_required``).
    """

    message = "Hanya Pengrajin (Artisan) atau Admin yang dapat mengelola produk."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_artisan_or_staff(request.user)
