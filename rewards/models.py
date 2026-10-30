from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Reward(models.Model):
    class Type(models.TextChoices):
        VOUCHER = "VOUCHER", "Voucher diskon"
        PHYSICAL = "PHYSICAL", "Barang fisik"

    name = models.CharField(max_length=120)
    code_prefix = models.CharField(max_length=20, default="RB")
    description = models.TextField(blank=True)
    reward_type = models.CharField(max_length=12, choices=Type.choices)
    points_required = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="rewards/vouchers/", blank=True)

    class Meta:
        ordering = ["points_required", "name"]
        verbose_name = "voucher"
        verbose_name_plural = "katalog voucher"

    def __str__(self):
        return self.name


class RewardRedemption(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Menunggu pemenuhan"
        FULFILLED = "FULFILLED", "Selesai"
        CANCELLED = "CANCELLED", "Dibatalkan"

    class VoucherStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Belum digunakan"
        USED = "USED", "Sudah digunakan"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reward_redemptions",
    )
    reward = models.ForeignKey(Reward, on_delete=models.PROTECT, related_name="redemptions")
    points_spent = models.PositiveIntegerField()
    discount_value_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    voucher_code = models.CharField(max_length=40, unique=True, null=True, blank=True)
    voucher_status = models.CharField(
        max_length=12,
        choices=VoucherStatus.choices,
        null=True,
        blank=True,
    )
    shipping_address = models.CharField(max_length=255, blank=True)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reward_redemptions_cancelled",
    )

    class Meta:
        ordering = ["-redeemed_at", "-pk"]

    def __str__(self):
        return f"{self.reward.name} — {self.user} ({self.get_status_display()})"


class PointTransaction(models.Model):
    """Immutable credits and debits in the user's points ledger."""

    class Kind(models.TextChoices):
        DONATION = "donation", "Verified donation"
        MONTHLY_DONATION_BONUS = "monthly_donation_bonus", "Monthly donation bonus"
        UPCYCLING_COMPLETED = "upcycling_completed", "Completed upcycling"
        REDEMPTION = "redemption", "Reward redemption"
        REWARD_REFUNDED = "reward_refunded", "Reward redemption refunded"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_transactions",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    points = models.IntegerField()
    weight_kg = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    source_reference = models.CharField(max_length=100)
    upcycling_request = models.ForeignKey(
        "upcycling.UpcyclingRequest",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="point_transactions",
    )
    donation = models.ForeignKey(
        "donasi.DonasiKain",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="point_transactions",
    )
    reward_redemption = models.ForeignKey(
        RewardRedemption,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="point_transactions",
    )
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "kind", "source_reference"),
                name="rewards_unique_user_kind_source",
            ),
            models.UniqueConstraint(
                fields=("upcycling_request", "kind"),
                condition=Q(upcycling_request__isnull=False),
                name="rewards_unique_upcycling_kind",
            ),
            models.UniqueConstraint(
                fields=("donation", "kind"),
                condition=Q(donation__isnull=False),
                name="rewards_unique_donation_kind",
            ),
            models.UniqueConstraint(
                fields=("reward_redemption", "kind"),
                condition=Q(reward_redemption__isnull=False),
                name="rewards_unique_redemption_kind",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        kind__in=(
                            "donation",
                            "monthly_donation_bonus",
                            "upcycling_completed",
                            "reward_refunded",
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
            models.CheckConstraint(
                condition=(
                    Q(upcycling_request__isnull=True) | Q(donation__isnull=True)
                )
                & (Q(upcycling_request__isnull=True) | Q(reward_redemption__isnull=True))
                & (Q(donation__isnull=True) | Q(reward_redemption__isnull=True))
                & (Q(upcycling_request__isnull=True) | Q(kind="upcycling_completed"))
                & (Q(donation__isnull=True) | Q(kind__in=("donation", "monthly_donation_bonus")))
                & (
                    Q(reward_redemption__isnull=True)
                    | Q(kind__in=("redemption", "reward_refunded"))
                ),
                name="rewards_point_source_at_most_one",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.points:+d} points ({self.kind})"
