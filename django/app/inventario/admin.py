from django.contrib import admin
from django.db import transaction
from .models import (
    Unidad, Material, Almacen, Movimiento, MovimientoDetalle, Existencia, Kardex,
    Traspaso, TraspasoDetalle,
    aplicar_movimiento_promedio, aplicar_traspaso
)

@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre","factor_base")
    search_fields = ("nombre",)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("descripcion","codigo","unidad_base","stock_min","stock_max","activo")
    list_filter = ("activo","unidad_base")
    search_fields = ("descripcion","codigo")

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)

class MovimientoDetalleInline(admin.TabularInline):
    model = MovimientoDetalle
    extra = 1

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ("id","fecha","tipo","almacen","referencia","usuario","aplicado")
    list_filter = ("tipo","almacen","fecha","aplicado")
    date_hierarchy = "fecha"
    inlines = [MovimientoDetalleInline]

    def get_readonly_fields(self, request, obj=None):
        ro = super().get_readonly_fields(request, obj)
        return ("aplicado",) + ro

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not form.instance.aplicado:
            with transaction.atomic():
                aplicar_movimiento_promedio(form.instance)

class TraspasoDetalleInline(admin.TabularInline):
    model = TraspasoDetalle
    extra = 1

@admin.register(Traspaso)
class TraspasoAdmin(admin.ModelAdmin):
    list_display = ("id","fecha","almacen_origen","almacen_destino","referencia","usuario","aplicado")
    list_filter = ("almacen_origen","almacen_destino","fecha","aplicado")
    date_hierarchy = "fecha"
    inlines = [TraspasoDetalleInline]

    def get_readonly_fields(self, request, obj=None):
        ro = super().get_readonly_fields(request, obj)
        return ("aplicado",) + ro

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not form.instance.aplicado:
            with transaction.atomic():
                aplicar_traspaso(form.instance)

@admin.register(Existencia)
class ExistenciaAdmin(admin.ModelAdmin):
    list_display = ("material","almacen","stock","costo_promedio")
    list_filter = ("almacen",)
    search_fields = ("material__descripcion","material__codigo")

@admin.register(Kardex)
class KardexAdmin(admin.ModelAdmin):
    list_display = ("fecha","material","almacen","tipo","cantidad_entrada","cantidad_salida","costo_unitario","saldo_stock","saldo_costo_promedio","referencia")
    list_filter = ("almacen","tipo","fecha","material")
    date_hierarchy = "fecha"
    search_fields = ("material__descripcion","material__codigo","referencia")
    readonly_fields = ("movimiento","material","almacen","fecha","tipo","cantidad_entrada","cantidad_salida","costo_unitario","saldo_stock","saldo_costo_promedio","referencia")

