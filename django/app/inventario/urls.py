# inventario/urls.py
from django.urls import path
from .views import inventario_home, export_kardex_xlsx, nota_pedido_imprimir

app_name = "inventario"

urlpatterns = [
    path("", inventario_home, name="home"),
    path("kardex/export/", export_kardex_xlsx, name="kardex_export"),
    path("nota/<int:pk>/imprimir/", nota_pedido_imprimir, name="nota_pedido_imprimir"),
]
