"""
Audit Dashboard Views for Owner-level visibility
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import csv
import json
from .models import AuditLog, Project
from .audit_service import AuditQueryHelper
from django.contrib.auth.models import User


def is_owner_or_admin(user):
    """Check if user is Owner (superuser) or Admin System"""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name="AdminSystem").exists()


@user_passes_test(is_owner_or_admin)
def audit_dashboard(request):
    """
    Main audit dashboard for Owners showing comprehensive system activity
    """
    # Get time range filter
    days = int(request.GET.get('days', 7))
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Get base queryset based on user permissions
    if request.user.is_superuser:
        base_logs = AuditLog.objects.all()
    else:
        owned_projects = Project.objects.filter(owner=request.user)
        base_logs = AuditLog.objects.filter(
            Q(project__in=owned_projects) | Q(user=request.user)
        )
    
    # Filter by date range
    recent_logs = base_logs.filter(timestamp__gte=cutoff_date)
    
    # Get summary statistics
    total_logs = recent_logs.count()
    unique_users = recent_logs.values('user').distinct().count()
    failed_operations = recent_logs.filter(success=False).count()
    high_severity_count = recent_logs.filter(severity__in=['high', 'critical']).count()
    
    # Get recent activity (last 50 entries)
    recent_activity = recent_logs.order_by('-timestamp')[:50]
    
    # Get activity by severity
    severity_stats = recent_logs.values('severity').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get activity by action type
    action_stats = recent_logs.values('action').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Get activity by project (for owners)
    project_stats = []
    if request.user.is_superuser:
        project_stats = recent_logs.exclude(project__isnull=True).values(
            'project__name', 'project__slug'
        ).annotate(count=Count('id')).order_by('-count')[:10]
    
    # Get security alerts (failed logins, unauthorized access, etc.)
    security_alerts = recent_logs.filter(
        Q(action__in=['login_failed', 'unauthorized_access_attempt']) |
        Q(severity='critical') |
        Q(success=False)
    ).order_by('-timestamp')[:20]
    
    context = {
        'days': days,
        'total_logs': total_logs,
        'unique_users': unique_users,
        'failed_operations': failed_operations,
        'high_severity_count': high_severity_count,
        'recent_activity': recent_activity,
        'severity_stats': severity_stats,
        'action_stats': action_stats,
        'project_stats': project_stats,
        'security_alerts': security_alerts,
        'is_owner': request.user.is_superuser,
    }
    
    return render(request, 'control_plane/audit_dashboard.html', context)


@user_passes_test(is_owner_or_admin)
def audit_logs_list(request):
    """
    Detailed audit logs list with filtering and search
    """
    # Get filters from request
    action_filter = request.GET.get('action', '')
    severity_filter = request.GET.get('severity', '')
    user_filter = request.GET.get('user', '')
    project_filter = request.GET.get('project', '')
    success_filter = request.GET.get('success', '')
    search = request.GET.get('search', '')
    days = int(request.GET.get('days', 30))
    
    # Build base query
    logs = AuditQueryHelper.get_all_logs_for_owner(request.user, limit=10000)
    
    # Apply date filter
    if days:
        cutoff_date = timezone.now() - timedelta(days=days)
        logs = logs.filter(timestamp__gte=cutoff_date)
    
    # Apply filters
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if severity_filter:
        logs = logs.filter(severity=severity_filter)
    
    if user_filter:
        logs = logs.filter(username__icontains=user_filter)
    
    if project_filter:
        logs = logs.filter(project_slug__icontains=project_filter)
    
    if success_filter:
        success_bool = success_filter.lower() == 'true'
        logs = logs.filter(success=success_bool)
    
    # Apply search
    if search:
        logs = logs.filter(
            Q(username__icontains=search) |
            Q(action__icontains=search) |
            Q(project_slug__icontains=search) |
            Q(details__icontains=search) |
            Q(target_object_repr__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page')
    page_logs = paginator.get_page(page_number)
    
    # Get unique values for filter dropdowns
    all_logs = AuditQueryHelper.get_all_logs_for_owner(request.user, limit=10000)
    filter_options = {
        'actions': all_logs.values_list('action', flat=True).distinct().order_by('action'),
        'severities': all_logs.values_list('severity', flat=True).distinct().order_by('severity'),
        'users': all_logs.exclude(username='').values_list('username', flat=True).distinct().order_by('username')[:100],
        'projects': all_logs.exclude(project_slug='').values_list('project_slug', flat=True).distinct().order_by('project_slug'),
    }
    
    context = {
        'logs': page_logs,
        'filter_options': filter_options,
        'current_filters': {
            'action': action_filter,
            'severity': severity_filter,
            'user': user_filter,
            'project': project_filter,
            'success': success_filter,
            'search': search,
            'days': days,
        },
        'total_count': logs.count(),
    }
    
    return render(request, 'control_plane/audit_logs_list.html', context)


@user_passes_test(is_owner_or_admin)
def audit_log_detail(request, log_id):
    """
    Detailed view of a single audit log entry
    """
    log = get_object_or_404(AuditLog, id=log_id)
    
    # Check permissions
    if not request.user.is_superuser:
        # Non-owners can only see logs for their projects or their own actions
        owned_projects = Project.objects.filter(owner=request.user)
        if log.project and log.project not in owned_projects and log.user != request.user:
            return render(request, 'control_plane/access_denied.html')
    
    # Get related logs (same user, same project, similar time)
    related_logs = AuditLog.objects.filter(
        Q(user=log.user) | Q(project=log.project),
        timestamp__range=[
            log.timestamp - timedelta(minutes=10),
            log.timestamp + timedelta(minutes=10)
        ]
    ).exclude(id=log.id).order_by('-timestamp')[:10]
    
    context = {
        'log': log,
        'related_logs': related_logs,
    }
    
    return render(request, 'control_plane/audit_log_detail.html', context)


@user_passes_test(is_owner_or_admin)
def security_dashboard(request):
    """
    Security-focused dashboard showing threats and suspicious activity
    """
    days = int(request.GET.get('days', 7))
    
    # Get security logs
    security_logs = AuditQueryHelper.get_security_logs(request.user, days=days)
    
    # Failed login attempts
    failed_logins = security_logs.filter(action='login_failed')
    failed_login_stats = failed_logins.values('details__attempted_username').annotate(
        count=Count('id'),
        latest=timezone.now()
    ).order_by('-count')[:10]
    
    # Unauthorized access attempts
    unauthorized_attempts = security_logs.filter(action='unauthorized_access_attempt')
    
    # High severity events
    high_severity_events = AuditQueryHelper.get_high_severity_logs(request.user, days=days)
    
    # IP address analysis
    ip_stats = security_logs.exclude(ip_address__isnull=True).values('ip_address').annotate(
        count=Count('id'),
        failed_count=Count('id', filter=Q(success=False))
    ).order_by('-failed_count')[:10]
    
    context = {
        'days': days,
        'security_logs': security_logs[:50],
        'failed_logins_count': failed_logins.count(),
        'failed_login_stats': failed_login_stats,
        'unauthorized_attempts': unauthorized_attempts[:20],
        'high_severity_events': high_severity_events[:30],
        'ip_stats': ip_stats,
        'total_security_events': security_logs.count(),
    }
    
    return render(request, 'control_plane/security_dashboard.html', context)


@user_passes_test(is_owner_or_admin)
def export_audit_logs(request):
    """
    Export audit logs to CSV for compliance and analysis
    """
    # Get filters (same as list view)
    action_filter = request.GET.get('action', '')
    severity_filter = request.GET.get('severity', '')
    user_filter = request.GET.get('user', '')
    project_filter = request.GET.get('project', '')
    days = int(request.GET.get('days', 30))
    
    # Build query
    logs = AuditQueryHelper.get_all_logs_for_owner(request.user, limit=50000)  # Limit exports
    
    if days:
        cutoff_date = timezone.now() - timedelta(days=days)
        logs = logs.filter(timestamp__gte=cutoff_date)
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    if severity_filter:
        logs = logs.filter(severity=severity_filter)
    if user_filter:
        logs = logs.filter(username__icontains=user_filter)
    if project_filter:
        logs = logs.filter(project_slug__icontains=project_filter)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Timestamp', 'Action', 'Severity', 'User', 'User Email', 'Project', 
        'Target Object', 'Success', 'IP Address', 'Request Path', 'Request Method',
        'Error Message', 'Details'
    ])
    
    # Write data
    for log in logs:
        writer.writerow([
            log.timestamp.isoformat(),
            log.get_action_display(),
            log.get_severity_display(),
            log.username or '',
            log.user_email or '',
            log.project_slug or '',
            log.target_object_repr or '',
            'Yes' if log.success else 'No',
            log.ip_address or '',
            log.request_path or '',
            log.request_method or '',
            log.error_message or '',
            json.dumps(log.details) if log.details else '',
        ])
    
    # Log the export action
    from .audit_service import AuditService
    AuditService.log_data_export(
        user=request.user,
        export_type='audit_logs_csv',
        record_count=logs.count(),
        request=request,
    )
    
    return response


@user_passes_test(is_owner_or_admin)
def audit_stats_api(request):
    """
    API endpoint for audit statistics (for dashboard charts)
    """
    days = int(request.GET.get('days', 7))
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Get logs for the user
    if request.user.is_superuser:
        logs = AuditLog.objects.filter(timestamp__gte=cutoff_date)
    else:
        owned_projects = Project.objects.filter(owner=request.user)
        logs = AuditLog.objects.filter(
            Q(project__in=owned_projects) | Q(user=request.user),
            timestamp__gte=cutoff_date
        )
    
    # Activity by day
    from django.db.models import TruncDate
    daily_activity = logs.extra({'date': 'date(timestamp)'}).values('date').annotate(
        count=Count('id'),
        failed_count=Count('id', filter=Q(success=False))
    ).order_by('date')
    
    # Activity by hour (last 24 hours)
    last_24h = timezone.now() - timedelta(hours=24)
    hourly_activity = logs.filter(timestamp__gte=last_24h).extra(
        {'hour': 'extract(hour from timestamp)'}
    ).values('hour').annotate(count=Count('id')).order_by('hour')
    
    # Top users by activity
    top_users = logs.exclude(username='').values('username').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    data = {
        'daily_activity': list(daily_activity),
        'hourly_activity': list(hourly_activity),
        'top_users': list(top_users),
        'total_logs': logs.count(),
        'failed_operations': logs.filter(success=False).count(),
        'high_severity': logs.filter(severity__in=['high', 'critical']).count(),
    }
    
    return JsonResponse(data)