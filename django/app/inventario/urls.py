# inventario/urls.py
from django.urls import path
from .views import inventario_home, export_kardex_xlsx

app_name = "inventario"

urlpatterns = [
    path("", inventario_home, name="home"),
    path("kardex/export/", export_kardex_xlsx, name="kardex_export"),
]
