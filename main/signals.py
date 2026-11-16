from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender="donasi.DonasiKain")
def remember_donation_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk)
            .values_list("status", flat=True)
            .first()
        )
    else:
        instance._previous_status = None


@receiver(post_save, sender="donasi.DonasiKain")
def notify_donation_status(sender, instance, created, **kwargs):
    if not created and instance.user_id and getattr(instance, "_previous_status", None) != instance.status:
        from .views import create_notification
        create_notification(
            instance.user,
            "Status donasi kain diperbarui",
            f"Pengajuan donasi '{instance.item_name}' sekarang: {instance.get_status_display()}.",
            notification_type="donation_updated",
            target_url="/donasi/history/",
        )


@receiver(pre_save, sender="upcycling.UpcyclingRequest")
def remember_upcycling_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk)
            .values_list("status", flat=True)
            .first()
        )
    else:
        instance._previous_status = None


@receiver(post_save, sender="upcycling.UpcyclingRequest")
def notify_upcycling_status(sender, instance, created, **kwargs):
    if not created and getattr(instance, "_previous_status", None) != instance.status:
        from .views import create_notification
        create_notification(
            instance.user,
            "Status permintaan upcycling diperbarui",
            f"Permintaan upcycling kamu sekarang: {instance.get_status_display()}.",
            notification_type="upcycling_updated",
            target_url="/upcycling/",
        )
