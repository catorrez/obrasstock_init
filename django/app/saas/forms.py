# saas/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import ProjectRole

class ClientAuthForm(AuthenticationForm):
    """
    Login de clientes: bloquea staff/superuser (ellos deben entrar por /admin).
    """
    def confirm_login_allowed(self, user):
        if user.is_staff or user.is_superuser:
            raise forms.ValidationError(
                _("Este acceso es solo para clientes. Usa /admin para entrar."),
                code="admin_forbidden",
            )

class InviteForm(forms.Form):
    email = forms.EmailField(
        required=False,
        help_text=_("Opcional. Si lo dejas vacío obtendrás un link compartible."),
    )
    role = forms.ChoiceField(
        choices=ProjectRole.choices,
        initial=ProjectRole.OPERATOR,
        help_text=_("Rol dentro del proyecto."),
    )
