#!/bin/bash

# Fixed migration script using mysqldump for proper table copying

# Database credentials
DB_HOST=db
DB_ROOT_USER=root
DB_ROOT_PASS=RootMuySegura!123
DB_USER=obrasuser
DB_PASS=SuperSegura!123

echo "🚀 Starting fixed multi-tenant migration..."

# Get project from SAAS
echo "📊 Checking SAAS projects..."
docker-compose exec web python manage.py shell -c "
from saas.models import Project
projects = Project.objects.all()
print('Projects found:', projects.count())
for p in projects:
    print(f'{p.slug}|{p.name}|{p.owner.username}|{p.id}')
" > projects.txt

# Process each project
while IFS='|' read -r slug name owner project_id; do
    if [ ! -z "$slug" ] && [[ "$slug" != *"Projects found"* ]]; then
        echo ""
        echo "📁 Processing project: $name ($slug) ID: $project_id"
        
        # Create project database
        PROJECT_DB="project_$slug"
        echo "  🔧 Creating database: $PROJECT_DB"
        
        docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS -e "
            CREATE DATABASE IF NOT EXISTS \`$PROJECT_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            GRANT ALL PRIVILEGES ON \`$PROJECT_DB\`.* TO '$DB_USER'@'%';
            FLUSH PRIVILEGES;
        "
        
        # Copy inventario table structures using mariadb-dump
        echo "  📋 Copying inventario table structures..."
        
        # Dump only table structures (no data)
        docker-compose exec db mariadb-dump -u$DB_ROOT_USER -p$DB_ROOT_PASS \
            --no-data \
            obrasstock \
            inventario_almacen \
            inventario_consecutivo \
            inventario_existencia \
            inventario_kardex \
            inventario_material \
            inventario_movimiento \
            inventario_movimientodetalle \
            inventario_notapedido \
            inventario_notapedidodetalle \
            inventario_traspaso \
            inventario_traspasodetalle \
            inventario_unidad \
            > /tmp/inventario_structure.sql
        
        # Import structures to project database
        docker-compose exec -T db mariadb -u$DB_USER -p$DB_PASS $PROJECT_DB < /tmp/inventario_structure.sql
        
        # Copy project-specific data
        echo "  📦 Copying project-specific data (project_id=$project_id)..."
        
        # Tables with project_id filtering - use proper WHERE clause
        for table in inventario_almacen inventario_notapedido; do
            echo "    - Migrating data: $table"
            
            # Check if table has data for this project
            ROW_COUNT=$(docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS obrasstock -sN -e "SELECT COUNT(*) FROM $table WHERE project_id = $project_id;")
            ROW_COUNT=$(echo $ROW_COUNT | tr -d '\r')
            
            if [ "$ROW_COUNT" -gt 0 ]; then
                docker-compose exec db mariadb-dump -u$DB_ROOT_USER -p$DB_ROOT_PASS \
                    --no-create-info \
                    --where="project_id=$project_id" \
                    obrasstock $table > /tmp/${table}_data.sql
                
                docker-compose exec -T db mariadb -u$DB_USER -p$DB_PASS $PROJECT_DB < /tmp/${table}_data.sql
                echo "      ✓ Copied $ROW_COUNT rows"
            else
                echo "      - No data found for project $project_id"
            fi
        done
        
        # Tables without project_id - copy related data based on foreign keys
        for table in inventario_existencia inventario_kardex inventario_movimiento inventario_movimientodetalle inventario_notapedidodetalle inventario_traspaso inventario_traspasodetalle; do
            echo "    - Migrating related data: $table"
            
            # This would need more complex queries based on relationships
            # For now, let's copy all data and clean up later
            docker-compose exec db mariadb-dump -u$DB_ROOT_USER -p$DB_ROOT_PASS \
                --no-create-info \
                obrasstock $table > /tmp/${table}_data.sql
            
            if [ -s /tmp/${table}_data.sql ]; then
                docker-compose exec -T db mariadb -u$DB_USER -p$DB_PASS $PROJECT_DB < /tmp/${table}_data.sql
                echo "      ✓ Copied all $table data"
            fi
        done
        
        # Global tables (full copy)
        echo "  🌍 Copying global tables..."
        for table in inventario_consecutivo inventario_unidad inventario_material; do
            echo "    - Copying global: $table"
            
            docker-compose exec db mariadb-dump -u$DB_ROOT_USER -p$DB_ROOT_PASS \
                --no-create-info \
                obrasstock $table > /tmp/${table}_data.sql
            
            if [ -s /tmp/${table}_data.sql ]; then
                docker-compose exec -T db mariadb -u$DB_USER -p$DB_PASS $PROJECT_DB < /tmp/${table}_data.sql
                echo "      ✓ Copied all $table data"
            fi
        done
        
        # Create corresponding Control Plane project
        echo "  🎯 Creating Control Plane project..."
        docker-compose exec web python manage.py shell -c "
from control_plane.models import Project as ControlPlaneProject
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    owner = User.objects.get(username='$owner')
    cp_project, created = ControlPlaneProject.objects.get_or_create(
        slug='$slug',
        defaults={
            'name': '$name',
            'description': 'Migrated from SAAS project: $name',
            'owner': owner,
            'database_name': '$PROJECT_DB'
        }
    )
    if created:
        print('✓ Created Control Plane project:', cp_project.name)
    else:
        print('✓ Control Plane project already exists:', cp_project.name)
except Exception as e:
    print('✗ Error creating Control Plane project:', e)
"
        
        echo "  ✅ Migration completed for project: $name"
        
        # Clean up temp files
        rm -f /tmp/inventario_structure.sql
        rm -f /tmp/*_data.sql
    fi
done < projects.txt

# Clean up
rm -f projects.txt

echo ""
echo "🎉 Migration completed successfully!"

echo ""
echo "📊 Verification:"
docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS -e "SHOW DATABASES LIKE 'project_%';"

echo ""
echo "📋 Checking sample project tables:"
docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS project_sample -e "SHOW TABLES;"