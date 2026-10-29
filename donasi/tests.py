from django.contrib import admin
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase
from django.urls import reverse

from rewards.models import PointTransaction

from .models import DonasiKain


User = get_user_model()


class VerifiedDonationRewardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="donor", password="pass")
        self.staff = User.objects.create_user(username="staff", is_staff=True)

    def test_admin_confirmation_awards_donation_points_once(self):
        donation = DonasiKain.objects.create(
            user=self.user,
            donor_name="Donor",
            whatsapp="081234567890",
            email="donor@example.com",
            address="Depok",
            city="Depok",
            item_name="Kain batik",
            donation_type=DonasiKain.JenisDonasi.KAIN,
            quantity=1,
            condition=DonasiKain.Kondisi.BAIK,
            description="Kain bekas layak pakai",
            donation_method=DonasiKain.MetodeDonasi.KIRIM_SENDIRI,
        )
        form_data = model_to_dict(donation)
        form_data.update(
            status=DonasiKain.Status.DIKONFIRMASI,
            verified_weight_kg="2.500",
        )
        form = admin.site._registry[DonasiKain].form(
            data=form_data,
            instance=donation,
        )
        self.assertTrue(form.is_valid(), form.errors)

        request = RequestFactory().post("/admin/donasi/donasikain/")
        request.user = self.staff
        donation_admin = admin.site._registry[DonasiKain]
        donation_admin.save_model(request, donation, form, change=True)
        donation_admin.save_model(request, donation, form, change=True)

        donation_points = PointTransaction.objects.get(
            donation=donation,
            kind=PointTransaction.Kind.DONATION,
        )
        bonus_points = PointTransaction.objects.get(
            donation=donation,
            kind=PointTransaction.Kind.MONTHLY_DONATION_BONUS,
        )
        self.assertEqual(donation_points.user, self.user)
        self.assertEqual(donation_points.points, 200)
        self.assertEqual(bonus_points.points, 25)
        self.assertEqual(
            PointTransaction.objects.filter(donation=donation).count(),
            2,
        )

    def test_unlinked_donation_remains_valid_without_reward_fields(self):
        donation = DonasiKain.objects.create(
            donor_name="Guest donor",
            whatsapp="081234567890",
            email="guest@example.com",
            address="Depok",
            city="Depok",
            item_name="Pakaian",
            donation_type=DonasiKain.JenisDonasi.PAKAIAN,
            quantity=1,
            condition=DonasiKain.Kondisi.BAIK,
            description="Donasi anonim",
            donation_method=DonasiKain.MetodeDonasi.KIRIM_SENDIRI,
        )
        self.assertIsNone(donation.user_id)
        self.assertIsNone(donation.verified_weight_kg)

    def test_authenticated_donation_is_linked_to_its_account(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("donasi:create"),
            {
                "donor_name": "Donor",
                "whatsapp": "081234567890",
                "email": "donor@example.com",
                "address": "Depok",
                "city": "Depok",
                "item_name": "Kain batik",
                "donation_type": DonasiKain.JenisDonasi.KAIN,
                "quantity": 1,
                "condition": DonasiKain.Kondisi.BAIK,
                "description": "Kain bekas layak pakai",
                "donation_method": DonasiKain.MetodeDonasi.KIRIM_SENDIRI,
            },
        )
        self.assertRedirects(response, reverse("donasi:history"))
        self.assertEqual(
            DonasiKain.objects.get(email="donor@example.com").user,
            self.user,
        )

# Create your tests here.
