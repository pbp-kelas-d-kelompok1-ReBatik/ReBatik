"""Helper kecil yang dipakai bersama oleh API DRF di beberapa app."""
from batik_custom.models import resolve_image_url


def absolute_image_url(request, image_field):
    """URL gambar absolut agar bisa dimuat langsung oleh aplikasi Flutter.

    ``resolve_image_url`` mengembalikan path relatif (``/static/...``) untuk
    katalog bawaan dan URL penuh untuk upload Cloudinary.
    """
    url = resolve_image_url(image_field)
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    return url
