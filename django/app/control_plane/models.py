from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import RegexValidator
import uuid


class ModuleRegistry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_core = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Module Registry"
    
    def __str__(self):
        return self.display_name




class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('archived', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True, validators=[
        RegexValidator(r'^[a-z][a-z0-9_]*$', 'Slug must start with letter and contain only lowercase letters, numbers, and underscores')
    ])
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    database_name = models.CharField(max_length=100, unique=True, editable=False)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='control_plane_owned_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.database_name:
            self.database_name = "obras_proj_{}".format(self.slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class ProjectModule(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='enabled_modules')
    module = models.ForeignKey(ModuleRegistry, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=True)
    enabled_at = models.DateTimeField(auto_now_add=True)
    enabled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ['project', 'module']
    
    def __str__(self):
        return "{} - {}".format(self.project.name, self.module.name)


class RoleType(models.Model):
    """
    RoleType model for project membership tracking only.
    
    Note: This model is NOT used for access control or privilege enforcement.
    Access control is handled by Django Groups and UserTypeService.
    
    This model exists solely to track user roles within specific projects
    for display and organizational purposes.
    """
    
    name = models.CharField(max_length=20, unique=True, help_text="Role identifier (e.g., 'project_admin', 'operator')")
    display_name = models.CharField(max_length=100, help_text="Human-readable role name")
    description = models.TextField(help_text="Role description for documentation")
    level = models.IntegerField(help_text="Display hierarchy level (lower=higher in hierarchy)")
    
    class Meta:
        ordering = ['level']
        verbose_name = "Project Role Type"
        verbose_name_plural = "Project Role Types"
    
    def __str__(self):
        return self.display_name


class ProjectMembership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='control_plane_memberships')
    role = models.ForeignKey(RoleType, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='control_plane_added_memberships')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'user']
    
    def __str__(self):
        return "{} - {} ({})".format(self.user.username, self.project.name, self.role.name)






class AuditLog(models.Model):
    # Comprehensive action types for complete audit coverage
    ACTION_CHOICES = [
        # Control Plane Operations
        ('create_project', 'Create Project'),
        ('update_project', 'Update Project'),
        ('delete_project', 'Delete Project'),
        ('add_user', 'Add User'),
        ('remove_user', 'Remove User'),
        ('change_role', 'Change Role'),
        ('grant_privilege', 'Grant Privilege'),
        ('revoke_privilege', 'Revoke Privilege'),
        ('enable_module', 'Enable Module'),
        ('disable_module', 'Disable Module'),
        
        # Authentication & Security
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('login_failed', 'Login Failed'),
        ('password_change', 'Password Change'),
        ('password_reset', 'Password Reset'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        
        # Application Operations
        ('create_record', 'Create Record'),
        ('update_record', 'Update Record'),
        ('delete_record', 'Delete Record'),
        ('view_record', 'View Record'),
        ('export_data', 'Export Data'),
        ('import_data', 'Import Data'),
        ('bulk_operation', 'Bulk Operation'),
        
        # System Operations
        ('admin_login', 'Admin Login'),
        ('system_config_change', 'System Config Change'),
        ('backup_created', 'Backup Created'),
        ('backup_restored', 'Backup Restored'),
        ('maintenance_mode', 'Maintenance Mode'),
        
        # Tenant Operations
        ('project_access', 'Project Access'),
        ('cross_project_access', 'Cross Project Access'),
        ('api_access', 'API Access'),
        ('unauthorized_access_attempt', 'Unauthorized Access Attempt'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='low')
    
    # User information
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True, help_text="Username at time of action (preserved even if user deleted)")
    user_email = models.EmailField(blank=True, help_text="Email at time of action")
    
    # Project/Tenant information
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    project_slug = models.CharField(max_length=100, blank=True, help_text="Project slug at time of action")
    
    # Target information (for operations on other users/objects)
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_targets')
    target_object_type = models.CharField(max_length=100, blank=True, help_text="Model name of target object")
    target_object_id = models.CharField(max_length=100, blank=True, help_text="ID of target object")
    target_object_repr = models.TextField(blank=True, help_text="String representation of target object")
    
    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.TextField(blank=True, help_text="URL path of the request")
    request_method = models.CharField(max_length=10, blank=True, help_text="HTTP method")
    referer = models.TextField(blank=True, help_text="HTTP referer")
    session_key = models.CharField(max_length=40, blank=True, help_text="Session key for tracking user sessions")
    
    # Change tracking
    old_values = models.JSONField(default=dict, blank=True, help_text="Previous values before change")
    new_values = models.JSONField(default=dict, blank=True, help_text="New values after change")
    details = models.JSONField(default=dict, help_text="Additional context and metadata")
    
    # Status and flags
    success = models.BooleanField(default=True, help_text="Whether the operation succeeded")
    error_message = models.TextField(blank=True, help_text="Error message if operation failed")
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return "{} by {} at {}".format(self.action, self.user, self.timestamp)
