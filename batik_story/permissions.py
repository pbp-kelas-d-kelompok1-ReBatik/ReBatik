from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStaffOrReadOnly(BasePermission):
    """Semua pengunjung boleh membaca; hanya staff yang boleh mengelola motif.

    Aturan yang sama dengan view web (add_batik, story_edit, delete_story
    memeriksa ``request.user.is_staff``).
    """

    message = "Hanya staff yang dapat mengelola cerita batik."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user.is_authenticated and request.user.is_staff)
