# core/views.py
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect
from django.http import HttpResponse

class SubdomainLoginView(auth_views.LoginView):
    """Login view that chooses template based on subdomain"""
    
    def get_template_names(self):
        host = self.request.get_host().split(":")[0]
        
        if host == "obrasstock.etvholding.com":
            return ['owner/login.html']
        elif host == "adminos.etvholding.com":
            return ['admin_system/login.html']
        elif host == "appos.etvholding.com":
            return ['portal/login.html']  # Use existing portal login
        else:
            return ['admin/login.html']  # Default
    
    def get_success_url(self):
        """Redirect authenticated users to their appropriate portal"""
        host = self.request.get_host().split(":")[0]
        
        # Redirect to appropriate portal after successful authentication
        if host == "obrasstock.etvholding.com":
            return '/owner/'
        elif host == "adminos.etvholding.com":
            return '/admin/'
        elif host == "appos.etvholding.com":
            return '/app/'
        else:
            return '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        host = self.request.get_host().split(":")[0]
        
        # Check if user is already authenticated  
        context['is_authenticated'] = self.request.user.is_authenticated
        context['username'] = self.request.user.username if self.request.user.is_authenticated else None
        
        if host == "obrasstock.etvholding.com":
            context.update({
                'title': 'OWNER SYSTEM Login',
                'site_header': 'ObrasStock Owner Console',
                'subdomain': 'owner',
                'user_type': 'OWNER',
                'access_level': 'Highest Access Level - System Owner'
            })
        elif host == "adminos.etvholding.com":
            context.update({
                'title': 'ADMIN SYSTEM Login',
                'site_header': 'ObrasStock Admin Console', 
                'subdomain': 'admin',
                'user_type': 'ADMIN SYSTEM',
                'access_level': 'Administrative Access - System Management'
            })
        elif host == "appos.etvholding.com":
            context.update({
                'title': 'PROJECT LOGIN',
                'site_header': 'ObrasStock Project Portal',
                'subdomain': 'project',
                'user_type': 'PROJECT USER',
                'access_level': 'Project Access - Operations & Management'
            })
            
        return context