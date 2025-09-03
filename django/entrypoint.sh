#!/bin/sh
set -e

echo "Esperando DB..."
python - <<'PY'
import os, time, MySQLdb
host=os.getenv('DB_HOST', 'db')
port=int(os.getenv('DB_PORT','3306'))
user=os.getenv('DB_USER')
pwd=os.getenv('DB_PASSWORD')
name=os.getenv('DB_NAME')
for i in range(60):  # ~120s
    try:
        MySQLdb.connect(host=host, port=port, user=user, passwd=pwd, db=name)
        print("DB OK")
        break
    except Exception as e:
        print("DB no lista aún...", e)
        time.sleep(2)
else:
    raise SystemExit("Timeout esperando DB")
PY

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Collectstatic..."
python manage.py collectstatic --noinput

echo "Levantando Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
