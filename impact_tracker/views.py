from django.shortcuts import render

from . import services


def dashboard(request):
    """Tampilkan dampak komunitas ReBatik secara publik.

    Halaman ini hanya membaca data dari aplikasi ``donasi`` dan
    ``upcycling``; tidak ada data pribadi donatur yang dikirim ke template.
    """
    period = request.GET.get("period", services.DEFAULT_PERIOD)
    if period not in services.PERIOD_CHOICES:
        period = services.DEFAULT_PERIOD

    donation_stats = services.get_donation_stats()
    upcycling_stats = services.get_upcycling_stats()

    context = {
        "donation_stats": donation_stats,
        "upcycling_stats": upcycling_stats,
        "journeys": services.get_journeys(donation_stats, upcycling_stats),
        "chart": services.get_monthly_chart(period),
        "period_options": services.get_period_options(period),
        "recent_activity": services.get_recent_activity(),
        "personal": (
            services.get_personal_stats(request.user)
            if request.user.is_authenticated
            else None
        ),
    }
    return render(request, "impact_tracker/dashboard.html", context)