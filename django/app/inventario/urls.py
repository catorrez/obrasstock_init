# inventario/urls.py
from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    # landing del módulo Inventario dentro del proyecto
    path("home/", views.home, name="home"),

    # endpoints que ya tenías
    path("kardex/export/", views.export_kardex_xlsx, name="kardex_export"),
    path("nota/<int:pk>/imprimir/", views.nota_pedido_imprimir, name="nota_pedido_imprimir"),
]
