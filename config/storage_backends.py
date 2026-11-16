"""Django file storage backed by Cloudinary for production uploads."""

import posixpath
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote

import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.files.storage import Storage
from django.core.exceptions import SuspiciousFileOperation


class CloudinaryMediaStorage(Storage):
    """Store new ImageField uploads in Cloudinary and serve their CDN URLs."""

    name_prefix = "cloudinary:"

    def get_available_name(self, name, max_length=None):
        """Use a short random name; Cloudinary IDs must never collide."""
        normalized_name = name.replace("\\", "/")
        folder, original_name = posixpath.split(normalized_name)
        extension = PurePosixPath(original_name).suffix
        random_name = f"{uuid.uuid4().hex}{extension}"

        if max_length is not None:
            available_length = max_length - len(folder) - (1 if folder else 0)
            if len(random_name) > available_length:
                extension_length = len(extension)
                random_part_length = available_length - extension_length
                if random_part_length < 1:
                    raise SuspiciousFileOperation(
                        "The upload path is too long for this image field."
                    )
                random_name = f"{uuid.uuid4().hex[:random_part_length]}{extension}"

        return posixpath.join(folder, random_name) if folder else random_name

    def exists(self, name):
        # get_available_name creates a random path and _save uses a UUID public ID.
        return False

    def _save(self, name, content):
        normalized_name = name.replace("\\", "/")
        folder, filename = posixpath.split(normalized_name)
        folder_parts = [part for part in folder.split("/") if part not in ("", ".")]
        if ".." in folder_parts:
            raise SuspiciousFileOperation("Invalid upload directory.")

        file_stem = PurePosixPath(filename).stem
        public_id = "/".join(["rebatik", *folder_parts, file_stem])

        if hasattr(content, "seek"):
            content.seek(0)

        uploaded_asset = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
            unique_filename=False,
        )
        return f"{self.name_prefix}{uploaded_asset['public_id']}"

    def url(self, name):
        public_id = self._cloudinary_public_id(name)
        if public_id:
            return cloudinary.CloudinaryImage(public_id).build_url(
                secure=True,
                fetch_format="auto",
                quality="auto",
            )

        # Preserve URLs for files already stored under the legacy MEDIA_URL.
        legacy_name = quote(str(name).lstrip("/"), safe="/")
        return f"{settings.MEDIA_URL.rstrip('/')}/{legacy_name}"

    def delete(self, name):
        public_id = self._cloudinary_public_id(name)
        if public_id:
            cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )

    @classmethod
    def _cloudinary_public_id(cls, name):
        name = str(name)
        if not name.startswith(cls.name_prefix):
            return None
        public_id = name[len(cls.name_prefix):]
        return public_id or None
