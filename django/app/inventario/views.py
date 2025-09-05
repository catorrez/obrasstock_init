# inventario/views.py (solo lo esencial)
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from datetime import datetime

from .models import Kardex, NotaPedido

@login_required(login_url="/app/login/")
def inventario_home(request, project_slug):
    # Muestra un dashboard simple o enlaces del módulo.
    return render(request, "inventario/home.html", {"project_slug": project_slug})

@login_required(login_url="/app/login/")
def export_kardex_xlsx(request, project_slug):
    from openpyxl import Workbook
    try:
        material_id = request.GET.get("material_id")
        almacen_id  = request.GET.get("almacen_id")
        desde = request.GET.get("desde")
        hasta = request.GET.get("hasta")

        qs = Kardex.objects.select_related("material","almacen").order_by("fecha","id")
        qs = qs.filter(project__slug=project_slug)

        if material_id: qs = qs.filter(material_id=int(material_id))
        if almacen_id:  qs = qs.filter(almacen_id=int(almacen_id))
        if desde:       qs = qs.filter(fecha__date__gte=datetime.strptime(desde,"%Y-%m-%d").date())
        if hasta:       qs = qs.filter(fecha__date__lte=datetime.strptime(hasta,"%Y-%m-%d").date())

        wb = Workbook(); ws = wb.active; ws.title = "Kardex"
        ws.append(["Fecha","Material","Almacén","Tipo","Ref","Entrada","Salida","Costo Unit","Saldo Stock","Saldo CP"])
        for k in qs:
            ws.append([
                k.fecha.strftime("%Y-%m-%d %H:%M"), str(k.material), str(k.almacen), k.tipo, k.referencia or "",
                float(k.cantidad_entrada), float(k.cantidad_salida), float(k.costo_unitario),
                float(k.saldo_stock), float(k.saldo_costo_promedio)
            ])
        resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = 'attachment; filename="kardex.xlsx"'
        wb.save(resp)
        return resp
    except Exception as e:
        return HttpResponseBadRequest(f"Error: {e}")

@login_required(login_url="/app/login/")
def nota_pedido_imprimir(request, project_slug, pk):
    nota = get_object_or_404(NotaPedido, pk=pk, project__slug=project_slug)
    return render(request, "inventario/nota_pedido_print.html", {"nota": nota})
