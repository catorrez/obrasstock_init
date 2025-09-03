from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.urls import reverse
from saas.models import Project

class Unidad(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    factor_base = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("1"), validators=[MinValueValidator(Decimal("0"))])
    def __str__(self): return self.nombre

class Material(models.Model):
    codigo = models.CharField(max_length=50, unique=True, null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    unidad_base = models.ForeignKey(Unidad, on_delete=models.PROTECT)
    stock_min = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    stock_max = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    activo = models.BooleanField(default=True)
    def __str__(self): return f"{self.codigo or ''} {self.descripcion}".strip()

class Almacen(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nombre

class Movimiento(models.Model):
    TIPO_CHOICES = (("ENTRADA","Entrada"),("SALIDA","Salida"),("AJUSTE","Ajuste"))
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    referencia = models.CharField(max_length=100, null=True, blank=True)
    usuario = models.CharField(max_length=100, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    aplicado = models.BooleanField(default=False)  # evita doble aplicación
    def __str__(self): return f"{self.get_tipo_display()} {self.fecha:%Y-%m-%d %H:%M} #{self.id}"

class MovimientoDetalle(models.Model):
    movimiento = models.ForeignKey(Movimiento, related_name="detalles", on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=18, decimal_places=6, validators=[MinValueValidator(Decimal("0"))])
    # Para ENTRADA/AJUSTE positivo podemos informar costo; en SALIDA se usa costo_promedio vigente
    costo_unitario = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

class Existencia(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE)
    stock = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    costo_promedio = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    class Meta: unique_together = (("material","almacen"),)
    def __str__(self): return f"{self.material} @ {self.almacen}: {self.stock} (CP {self.costo_promedio})"

class Kardex(models.Model):
    movimiento = models.ForeignKey(Movimiento, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    fecha = models.DateTimeField()
    tipo = models.CharField(max_length=10)  # ENTRADA/SALIDA/AJUSTE
    referencia = models.CharField(max_length=100, null=True, blank=True)
    cantidad_entrada = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    cantidad_salida = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    costo_unitario = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    saldo_stock = models.DecimalField(max_digits=18, decimal_places=6)
    saldo_costo_promedio = models.DecimalField(max_digits=18, decimal_places=6)
    class Meta: ordering = ["fecha","id"]

# ---- Traspasos ----
class Traspaso(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    almacen_origen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="traspasos_salida")
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="traspasos_entrada")
    referencia = models.CharField(max_length=100, null=True, blank=True)
    usuario = models.CharField(max_length=100, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    aplicado = models.BooleanField(default=False)
    def __str__(self): return f"TRASP #{self.id} {self.almacen_origen} → {self.almacen_destino}"

class TraspasoDetalle(models.Model):
    traspaso = models.ForeignKey(Traspaso, related_name="detalles", on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=18, decimal_places=6, validators=[MinValueValidator(Decimal("0"))])
    # opcionalmente permitir costo explícito para destino; si no, se usa CP del origen
    costo_unitario_destino = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

# ---- Lógica de negocio ----
# ---- Lógica de negocio ----
def aplicar_movimiento_promedio(movimiento: Movimiento):
    """
    Aplica los detalles del movimiento a Existencias y genera líneas de Kardex (Promedio Ponderado).
    """
    from django.utils import timezone
    from django.conf import settings
    if movimiento.aplicado:
        return
    assert movimiento.pk, "El movimiento debe estar guardado antes de aplicar"

    with transaction.atomic():
        for det in movimiento.detalles.select_related("material"):
            # Existencia POR PROYECTO
            existencia, _ = Existencia.objects.select_for_update().get_or_create(
                project=movimiento.project,
                material=det.material,
                almacen=movimiento.almacen,
            )
            cp = existencia.costo_promedio or Decimal("0")
            st = existencia.stock or Decimal("0")
            cant = det.cantidad
            costo_in = det.costo_unitario or Decimal("0")

            tipo = movimiento.tipo
            if tipo == "AJUSTE" and cant > 0 and not det.costo_unitario:
                tipo_efectivo = "ENTRADA"; costo_in = cp
            elif tipo == "AJUSTE" and cant > 0:
                tipo_efectivo = "ENTRADA"
            else:
                tipo_efectivo = tipo

            if tipo_efectivo == "ENTRADA":
                nuevo_stock = st + cant
                nuevo_cp = ((st*cp) + (cant*costo_in)) / (nuevo_stock) if nuevo_stock > 0 else cp
                existencia.stock = nuevo_stock
                existencia.costo_promedio = nuevo_cp
                Kardex.objects.create(
                    project=movimiento.project,
                    movimiento=movimiento,
                    material=det.material,
                    almacen=movimiento.almacen,
                    fecha=movimiento.fecha or timezone.now(),
                    tipo=tipo,
                    referencia=movimiento.referencia,
                    cantidad_entrada=cant,
                    cantidad_salida=Decimal("0"),
                    costo_unitario=costo_in,
                    saldo_stock=nuevo_stock,
                    saldo_costo_promedio=nuevo_cp,
                )
            else:  # SALIDA / AJUSTE negativo
                nuevo_stock = st - cant
                if (nuevo_stock < 0) and (not getattr(settings, "ALLOW_STOCK_NEGATIVE", False)):
                    raise ValueError(f"Stock insuficiente para {det.material} en {movimiento.almacen}: {st} - {cant} < 0")
                existencia.stock = nuevo_stock
                # CP no cambia en salidas
                Kardex.objects.create(
                    project=movimiento.project,
                    movimiento=movimiento,
                    material=det.material,
                    almacen=movimiento.almacen,
                    fecha=movimiento.fecha or timezone.now(),
                    tipo=tipo,
                    referencia=movimiento.referencia,
                    cantidad_entrada=Decimal("0"),
                    cantidad_salida=cant,
                    costo_unitario=cp,
                    saldo_stock=nuevo_stock,
                    saldo_costo_promedio=cp,
                )
            existencia.save()
        movimiento.aplicado = True
        movimiento.save(update_fields=["aplicado"])


def aplicar_traspaso(traspaso: Traspaso):
    """
    Crea un movimiento SALIDA en origen y ENTRADA en destino por cada detalle.
    La ENTRADA se valora al CP del origen (o costo_unitario_destino si viene informado).
    """
    from django.utils import timezone
    if traspaso.aplicado:
        return
    assert traspaso.pk, "Guardar el traspaso antes de aplicar"

    with transaction.atomic():
        # 1) SALIDA origen
        mov_out = Movimiento.objects.create(
            project=traspaso.project,
            tipo="SALIDA",
            almacen=traspaso.almacen_origen,
            referencia=f"TRASP-{traspaso.id}",
            usuario=traspaso.usuario,
            observaciones=traspaso.observaciones,
        )
        for d in traspaso.detalles.select_related("material"):
            MovimientoDetalle.objects.create(
                movimiento=mov_out, material=d.material, cantidad=d.cantidad
            )

        aplicar_movimiento_promedio(mov_out)

        # 2) ENTRADA destino (costo = CP del origen o costo explícito)
        mov_in = Movimiento.objects.create(
            project=traspaso.project,
            tipo="ENTRADA",
            almacen=traspaso.almacen_destino,
            referencia=f"TRASP-{traspaso.id}",
            usuario=traspaso.usuario,
            observaciones=traspaso.observaciones,
        )
        for d in traspaso.detalles.select_related("material"):
            try:
                cp_origen = Existencia.objects.get(
                    project=traspaso.project,
                    material=d.material,
                    almacen=traspaso.almacen_origen,
                ).costo_promedio
            except Existencia.DoesNotExist:
                cp_origen = Decimal("0")
            costo_dest = d.costo_unitario_destino if d.costo_unitario_destino is not None else cp_origen
            MovimientoDetalle.objects.create(
                movimiento=mov_in, material=d.material, cantidad=d.cantidad, costo_unitario=costo_dest
            )

        aplicar_movimiento_promedio(mov_in)

        traspaso.aplicado = True
        traspaso.save(update_fields=["aplicado"])

from django.urls import reverse
from django.utils import timezone

# --- Consecutivos por PROYECTO ---
class Consecutivo(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)  # <-- temporalmente nullable
    nombre  = models.CharField(max_length=50)
    valor   = models.PositiveIntegerField(default=0)
    class Meta:
        unique_together = (("project","nombre"),)
    def __str__(self): return f"{self.project} · {self.nombre}: {self.valor}"

def next_consecutivo(project, nombre: str) -> int:
    with transaction.atomic():
        c, _ = Consecutivo.objects.select_for_update().get_or_create(
            project=project, nombre=nombre, defaults={'valor': 0}
        )
        c.valor += 1
        c.save(update_fields=['valor'])
        return c.valor

from django.urls import reverse

class NotaPedido(models.Model):
    ESTADOS = (("BORRADOR","Borrador"), ("ENVIADA","Enviada"),
               ("APROBADA","Aprobada"), ("RECHAZADA","Rechazada"),
               ("CERRADA","Cerrada"))

    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)  # ← si recién migras, déjalo null=True
    numero  = models.CharField(max_length=16, unique=True, blank=True)   # p.ej. P00003
    fecha   = models.DateField(default=timezone.now)
    almacen = models.ForeignKey('Almacen', on_delete=models.PROTECT)
    obra    = models.CharField(max_length=150, help_text="Obra/Proyecto")
    referencia   = models.CharField(max_length=100, null=True, blank=True)
    solicitante  = models.CharField(max_length=100, null=True, blank=True)
    aprobado_por = models.CharField(max_length=100, null=True, blank=True)
    observaciones= models.TextField(null=True, blank=True)
    estado  = models.CharField(max_length=10, choices=ESTADOS, default="BORRADOR")
    creado  = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Nota de pedido"
        verbose_name_plural = "Notas de pedido"

    def __str__(self): return self.numero or f"NP #{self.id}"

    @property
    def total(self):
        from django.db.models import Sum, F, DecimalField
        agg = self.detalles.aggregate(t=Sum(F("cantidad")*F("precio"),
                                            output_field=DecimalField(max_digits=18, decimal_places=6)))
        return agg["t"] or Decimal("0")

    def save(self, *args, **kwargs):
        # Genera número por PROYECTO
        if not self.numero:
            if not self.project:
                # seguridad: si no hay project, usa el del almacén si lo tienes en tus modelos
                try:
                    self.project = self.almacen.project
                except Exception:
                    pass
            n = next_consecutivo(self.project, "nota_pedido")
            self.numero = f"P{n:05d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # usa el slug del proyecto para /p/<project_slug>/nota/<pk>/imprimir/
        slug = getattr(self.project, "slug", None)
        if not slug:
            try:
                slug = self.almacen.project.slug
            except Exception:
                return "#"
        return reverse("nota_pedido_imprimir", kwargs={"project_slug": slug, "pk": self.pk})

class NotaPedidoDetalle(models.Model):
    nota = models.ForeignKey(NotaPedido, related_name="detalles", on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.PROTECT, null=True, blank=True)
    descripcion = models.CharField(max_length=255, help_text="Si no eliges material, escribe la descripción manual")
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=18, decimal_places=6, validators=[MinValueValidator(Decimal("0"))])
    precio = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))

    def __str__(self): return f"{self.descripcion} x {self.cantidad}"

    @property
    def subtotal(self): return (self.cantidad or 0) * (self.precio or 0)
