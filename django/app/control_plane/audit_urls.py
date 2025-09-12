"""
URL patterns for audit logging views
"""
from django.urls import path
from . import audit_views

app_name = 'audit'

urlpatterns = [
    # Main audit dashboard
    path('', audit_views.audit_dashboard, name='dashboard'),
    
    # Detailed audit logs list with filtering
    path('logs/', audit_views.audit_logs_list, name='logs_list'),
    
    # Individual audit log detail
    path('logs/<uuid:log_id>/', audit_views.audit_log_detail, name='log_detail'),
    
    # Security-focused dashboard
    path('security/', audit_views.security_dashboard, name='security_dashboard'),
    
    # Export audit logs to CSV
    path('export/', audit_views.export_audit_logs, name='export_logs'),
    
    # API endpoint for dashboard statistics
    path('api/stats/', audit_views.audit_stats_api, name='stats_api'),
]