def get_user_role(user):
    """
    Roles:
    - guest
    - eco_member
    - artisan
    - admin
    """

    if not user.is_authenticated:
        return "guest"

    user_groups = set(user.groups.values_list("name", flat=True))

    if user.is_superuser or "Admin" in user_groups:
        return "admin"

    if "Artisan" in user_groups:
        return "artisan"

    return "eco_member"