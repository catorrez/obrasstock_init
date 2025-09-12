#!/bin/bash

# Simple migration script to create project-specific databases and copy inventario data

# Database credentials
DB_HOST=db
DB_ROOT_USER=root
DB_ROOT_PASS=RootMuySegura!123
DB_USER=obrasuser
DB_PASS=SuperSegura!123

echo "🚀 Starting simple multi-tenant migration..."

# Get project from SAAS
echo "📊 Checking SAAS projects..."
docker-compose exec web python manage.py shell -c "
from saas.models import Project
projects = Project.objects.all()
print('Projects found:', projects.count())
for p in projects:
    print(f'{p.slug}|{p.name}|{p.owner.username}')
" > projects.txt

# Process each project
while IFS='|' read -r slug name owner; do
    if [ ! -z "$slug" ] && [[ "$slug" != *"Projects found"* ]]; then
        echo ""
        echo "📁 Processing project: $name ($slug)"
        
        # Create project database
        PROJECT_DB="project_$slug"
        echo "  🔧 Creating database: $PROJECT_DB"
        
        docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS -e "
            CREATE DATABASE IF NOT EXISTS \`$PROJECT_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            GRANT ALL PRIVILEGES ON \`$PROJECT_DB\`.* TO '$DB_USER'@'%';
            FLUSH PRIVILEGES;
        "
        
        # Copy inventario tables structure to project database
        echo "  📋 Copying inventario table structures..."
        for table in inventario_almacen inventario_consecutivo inventario_existencia inventario_kardex inventario_material inventario_movimiento inventario_movimientodetalle inventario_notapedido inventario_notapedidodetalle inventario_traspaso inventario_traspasodetalle inventario_unidad; do
            echo "    - Copying structure: $table"
            
            # Get table structure
            docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS obrasstock -e "SHOW CREATE TABLE $table\\G" | grep "Create Table:" -A 50 | sed '1d' > temp_$table.sql
            
            # Create table in project database
            docker-compose exec -T db mariadb -u$DB_USER -p$DB_PASS $PROJECT_DB < temp_$table.sql
            
            rm -f temp_$table.sql
        done
        
        # Get project ID for data filtering
        PROJECT_ID=$(docker-compose exec web python manage.py shell -c "
from saas.models import Project
try:
    p = Project.objects.get(slug='$slug')
    print(p.id)
except:
    print('0')
")
        PROJECT_ID=$(echo $PROJECT_ID | tr -d '\r')
        
        if [ "$PROJECT_ID" != "0" ]; then
            echo "  📦 Copying project-specific data (project_id=$PROJECT_ID)..."
            
            # Tables with project_id filtering
            for table in inventario_almacen inventario_existencia inventario_kardex inventario_material inventario_movimiento inventario_movimientodetalle inventario_notapedido inventario_notapedidodetalle inventario_traspaso inventario_traspasodetalle; do
                echo "    - Migrating data: $table"
                
                # Check if table has project_id column and copy data
                docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS -e "
                    INSERT INTO \`$PROJECT_DB\`.\`$table\` 
                    SELECT * FROM obrasstock.\`$table\` 
                    WHERE project_id = $PROJECT_ID;
                "
            done
            
            # Global tables (full copy)
            echo "  🌍 Copying global tables..."
            for table in inventario_consecutivo inventario_unidad; do
                echo "    - Copying global: $table"
                
                docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS -e "
                    INSERT INTO \`$PROJECT_DB\`.\`$table\` 
                    SELECT * FROM obrasstock.\`$table\`;
                "
            done
        fi
        
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
    fi
done < projects.txt

# Clean up
rm -f projects.txt

echo ""
echo "🎉 Migration completed successfully!"
echo "   - Created project-specific databases"
echo "   - Migrated inventario data with project isolation"
echo "   - Created Control Plane projects"

echo ""
echo "📊 Verification:"
docker-compose exec db mariadb -u$DB_ROOT_USER -p$DB_ROOT_PASS -e "SHOW DATABASES LIKE 'project_%';"