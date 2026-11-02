import re

from django import forms


def normalize_indonesian_whatsapp(value):
    """Validate and normalize an Indonesian mobile number to +628... format."""
    normalized = re.sub(r"[\s().-]", "", value or "")

    if not re.fullmatch(r"(?:0|\+?62)8[1-9][0-9]{7,10}", normalized):
        raise forms.ValidationError(
            "Masukkan nomor HP Indonesia yang valid, misalnya +6281234567890."
        )

    if normalized.startswith("0"):
        return f"+62{normalized[1:]}"
    if normalized.startswith("62"):
        return f"+{normalized}"
    return normalized

