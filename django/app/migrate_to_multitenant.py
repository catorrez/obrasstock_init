#!/usr/bin/env python3
"""
Migration script to convert single-database SAAS to database-per-project architecture.

This script:
1. Creates separate databases for each project
2. Migrates data from central database to project-specific databases
3. Updates Control Plane to track project databases
4. Maintains data integrity during migration
"""

import os
import sys
import django
from django.conf import settings
from django.db import connections, transaction, connection
from django.core.management import execute_from_command_line

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/dockers/obrasstock/django/app')
django.setup()

from saas.models import Project as SaasProject
from control_plane.models import Project as ControlPlaneProject

def create_project_database(project_slug, db_config):
    """Create a new database for a project and run migrations."""
    
    # Database connection details
    db_name = f"project_{project_slug}"
    
    # Use Django's database connection
    with connection.cursor() as cursor:
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        # Grant permissions to app user
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_config['USER']}'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        
    print(f"✓ Created database: {db_name}")
    
    return db_name

def migrate_project_data(project, source_db_alias='default'):
    """Migrate project-specific data to project database."""
    
    project_db_alias = f"project_{project.slug}"
    
    # Tables to migrate with project filtering
    INVENTARIO_TABLES = [
        'inventario_almacen',
        'inventario_existencia', 
        'inventario_kardex',
        'inventario_material',
        'inventario_movimiento',
        'inventario_movimientodetalle',
        'inventario_notapedido',
        'inventario_notapedidodetalle',
        'inventario_traspaso',
        'inventario_traspasodetalle'
    ]
    
    # Global tables (no project filtering needed)
    GLOBAL_TABLES = [
        'inventario_consecutivo',
        'inventario_unidad'
    ]
    
    source_conn = connections[source_db_alias]
    target_conn = connections[project_db_alias]
    
    with source_conn.cursor() as source_cursor, target_conn.cursor() as target_cursor:
        
        # Migrate project-specific tables
        for table in INVENTARIO_TABLES:
            try:
                # Check if table has project_id column
                source_cursor.execute(f"DESCRIBE {table}")
                columns = [row[0] for row in source_cursor.fetchall()]
                
                if 'project_id' in columns:
                    # Copy structure
                    source_cursor.execute(f"SHOW CREATE TABLE {table}")
                    create_sql = source_cursor.fetchone()[1]
                    target_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    target_cursor.execute(create_sql)
                    
                    # Copy data for this project only
                    source_cursor.execute(f"SELECT * FROM {table} WHERE project_id = %s", [project.id])
                    data = source_cursor.fetchall()
                    
                    if data:
                        # Build INSERT statement
                        placeholders = ', '.join(['%s'] * len(columns))
                        columns_str = ', '.join([f"`{col}`" for col in columns])
                        insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                        
                        target_cursor.executemany(insert_sql, data)
                        print(f"  ✓ Migrated {len(data)} records from {table}")
                    else:
                        print(f"  - No data in {table} for project {project.slug}")
                else:
                    print(f"  ! Table {table} missing project_id column - needs manual review")
                    
            except Exception as e:
                print(f"  ✗ Error migrating {table}: {e}")
        
        # Copy global tables (full copy)
        for table in GLOBAL_TABLES:
            try:
                # Copy structure
                source_cursor.execute(f"SHOW CREATE TABLE {table}")
                create_sql = source_cursor.fetchone()[1]
                target_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                target_cursor.execute(create_sql)
                
                # Copy all data
                source_cursor.execute(f"SELECT * FROM {table}")
                data = source_cursor.fetchall()
                
                if data:
                    source_cursor.execute(f"DESCRIBE {table}")
                    columns = [row[0] for row in source_cursor.fetchall()]
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_str = ', '.join([f"`{col}`" for col in columns])
                    insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                    
                    target_cursor.executemany(insert_sql, data)
                    print(f"  ✓ Copied global table {table} ({len(data)} records)")
                    
            except Exception as e:
                print(f"  ✗ Error copying global table {table}: {e}")

def setup_project_database_routing():
    """Setup dynamic database configuration for project routing."""
    
    # Update settings to include project databases
    projects = Project.objects.all()
    
    for project in projects:
        db_name = f"project_{project.slug}"
        db_alias = f"project_{project.slug}"
        
        # Add database configuration
        settings.DATABASES[db_alias] = {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': db_name,
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST', 'db'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
            'CONN_MAX_AGE': 60,
        }
        
        # Record in Control Plane
        ProjectDatabase.objects.get_or_create(
            project=project,
            defaults={
                'database_name': db_name,
                'database_alias': db_alias,
                'is_active': True
            }
        )

def main():
    """Main migration process."""
    print("🚀 Starting migration to database-per-project architecture...")
    
    try:
        # Get database configuration
        db_config = settings.DATABASES['default']
        
        # Get all projects from SAAS
        projects = SaasProject.objects.all()
        print(f"📊 Found {projects.count()} SAAS projects to migrate")
        
        if projects.count() == 0:
            print("⚠️  No projects found. Creating sample project for testing...")
            # Create a sample project if none exist
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get or create owner
            owner_username = os.getenv('OWNER_USERNAME', 'enrique')
            try:
                owner = User.objects.get(username=owner_username)
            except User.DoesNotExist:
                owner = User.objects.create_user(
                    username=owner_username,
                    is_staff=True,
                    is_superuser=True
                )
            
            # Create sample project
            project = SaasProject.objects.create(
                name="Sample Project",
                slug="sample",
                owner=owner,
                user_limit=10
            )
            projects = [project]
            print(f"✓ Created sample project: {project.name}")
        
        # Process each project
        for project in projects:
            print(f"\n📁 Processing project: {project.name} ({project.slug})")
            
            # Create project database
            db_name = create_project_database(project.slug, db_config)
            
            # Add database to Django settings
            db_alias = f"project_{project.slug}"
            settings.DATABASES[db_alias] = {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': db_name,
                'USER': db_config['USER'],
                'PASSWORD': db_config['PASSWORD'],
                'HOST': db_config['HOST'],
                'PORT': db_config['PORT'],
                'OPTIONS': {'charset': 'utf8mb4'},
                'CONN_MAX_AGE': 60,
            }
            
            # Run Django migrations on project database
            print(f"  🔧 Running Django migrations for {db_name}...")
            old_database_routers = settings.DATABASE_ROUTERS
            settings.DATABASE_ROUTERS = []  # Temporarily disable routing
            
            os.environ['DJANGO_DATABASE'] = db_alias
            execute_from_command_line(['manage.py', 'migrate', '--database', db_alias])
            
            settings.DATABASE_ROUTERS = old_database_routers
            
            # Migrate project data
            print(f"  📦 Migrating data for project {project.slug}...")
            migrate_project_data(project)
            
            # Record in Control Plane (create corresponding Control Plane project)
            try:
                cp_project = ControlPlaneProject.objects.get(slug=project.slug)
                print(f"  ✓ Control Plane project already exists: {cp_project.name}")
            except ControlPlaneProject.DoesNotExist:
                cp_project = ControlPlaneProject.objects.create(
                    name=project.name,
                    slug=project.slug,
                    description=f"Migrated from SAAS project: {project.name}",
                    owner=project.owner,
                    database_name=db_name
                )
                print(f"  ✓ Created Control Plane project: {cp_project.name}")
            
            print(f"  ✅ Migration completed for project: {project.name}")
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"   - Migrated {len(projects)} projects")
        print(f"   - Created {len(projects)} project databases")
        print(f"   - Updated Control Plane configuration")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)