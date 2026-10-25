from django.conf import settings
from django.db import models
from django.db.models import Q


class PointTransaction(models.Model):
    """An immutable credit or debit in a user's points ledger."""

    class Kind(models.TextChoices):
        DONATION = "donation", "Verified donation"
        MONTHLY_DONATION_BONUS = "monthly_donation_bonus", "Monthly donation bonus"
        UPCYCLING_COMPLETED = "upcycling_completed", "Completed upcycling"
        REDEMPTION = "redemption", "Reward redemption"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_transactions",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    points = models.IntegerField()
    weight_kg = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )
    source_reference = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "kind", "source_reference"),
                name="rewards_unique_user_kind_source",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        kind__in=(
                            "donation",
                            "monthly_donation_bonus",
                            "upcycling_completed",
                        ),
                        points__gt=0,
                    )
                    | Q(kind="redemption", points__lt=0)
                ),
                name="rewards_points_sign_matches_kind",
            ),
            models.CheckConstraint(
                condition=Q(weight_kg__isnull=True) | Q(weight_kg__gt=0),
                name="rewards_donation_weight_positive",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.points:+d} points ({self.kind})"
