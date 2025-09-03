# inventario/views.py
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from saas.models import Project, Membership
from .models import Kardex, NotaPedido


def _user_is_member(project: Project, user) -> bool:
    if not user.is_authenticated:
        return False
    return Membership.objects.filter(project=project, user=user).exists()


@login_required(login_url="/app/login/")
def home(request, project_slug):
    """
    Landing del módulo de Inventario dentro de un proyecto.
    Solo accesible para miembros del proyecto.
    """
    project = get_object_or_404(Project, slug=project_slug)
    if not _user_is_member(project, request.user):
        return HttpResponseForbidden("No eres miembro de este proyecto.")

    return render(request, "inventario/home.html", {"project": project})


@login_required(login_url="/app/login/")
def export_kardex_xlsx(request, project_slug):
    """
    Exporta el Kardex a XLSX, filtrado por proyecto (y filtros opcionales en querystring).
    Importamos openpyxl DENTRO de la función para no romper el arranque si no está instalado.
    """
    project = get_object_or_404(Project, slug=project_slug)
    if not _user_is_member(project, request.user):
        return HttpResponseForbidden("No eres miembro de este proyecto.")

    try:
        # Import local para evitar fallos en el arranque si falta la dependencia
        from openpyxl import Workbook

        material_id = request.GET.get("material_id")
        almacen_id  = request.GET.get("almacen_id")
        desde = request.GET.get("desde")  # YYYY-MM-DD
        hasta = request.GET.get("hasta")  # YYYY-MM-DD

        qs = (
            Kardex.objects
            .select_related("material", "almacen")
            .filter(project=project)            # << acotar por proyecto
            .order_by("fecha", "id")
        )

        if material_id:
            qs = qs.filter(material_id=int(material_id))
        if almacen_id:
            qs = qs.filter(almacen_id=int(almacen_id))
        if desde:
            qs = qs.filter(fecha__date__gte=datetime.strptime(desde, "%Y-%m-%d").date())
        if hasta:
            qs = qs.filter(fecha__date__lte=datetime.strptime(hasta, "%Y-%m-%d").date())

        wb = Workbook()
        ws = wb.active
        ws.title = "Kardex"
        ws.append([
            "Fecha", "Material", "Almacén", "Tipo", "Ref",
            "Entrada", "Salida", "Costo Unit", "Saldo Stock", "Saldo CP"
        ])
        for k in qs:
            ws.append([
                k.fecha.strftime("%Y-%m-%d %H:%M"),
                str(k.material),
                str(k.almacen),
                k.tipo,
                k.referencia or "",
                float(k.cantidad_entrada),
                float(k.cantidad_salida),
                float(k.costo_unitario),
                float(k.saldo_stock),
                float(k.saldo_costo_promedio),
            ])

        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = 'attachment; filename="kardex.xlsx"'
        wb.save(resp)
        return resp

    except Exception as e:
        return HttpResponseBadRequest(f"Error: {e}")


@login_required(login_url="/app/login/")
def nota_pedido_imprimir(request, project_slug, pk):
    """
    Imprime una Nota de Pedido del proyecto.
    """
    project = get_object_or_404(Project, slug=project_slug)
    if not _user_is_member(project, request.user):
        return HttpResponseForbidden("No eres miembro de este proyecto.")

    nota = get_object_or_404(NotaPedido, pk=pk, project=project)
    return render(request, "inventario/nota_pedido_print.html", {"nota": nota, "project": project})
