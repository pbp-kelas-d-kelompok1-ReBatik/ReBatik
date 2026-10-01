from django.shortcuts import render
from django.shortcuts import render
from .models import Product, DropOffPoint

# Create your views here.
def marketplace_home(request):
    products = Product.objects.filter(is_deleted=False)
    context = {
        'products': products,
    }
    return render(request, 'marketplace/index.html', context)

def dropoff_list(request):
    drop_points = DropOffPoint.objects.all().order_by('city')
    # Ambil list kota unik untuk filter tab
    cities = DropOffPoint.objects.values_list('city', flat=True).distinct()
    context = {
        'drop_points': drop_points,
        'cities': sorted(list(cities)),
    }
    return render(request, 'marketplace/dropoff.html', context)
