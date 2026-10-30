from django.conf import settings
from django.db import models

class Notification(models.Model):
    TYPE_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("register", "Pendaftaran"),
        ("order_created", "Pesanan berhasil"),
        ("order_updated", "Pembaruan pesanan"),
        ("order_cancelled", "Pesanan dibatalkan"),
        ("donation_updated", "Pembaruan donasi"),
        ("upcycling_updated", "Pembaruan upcycling"),
        ("general", "Informasi"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="general")
    target_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.title} - {self.user}"
