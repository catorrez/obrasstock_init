FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Paquetes del sistema:
# - default-libmysqlclient-dev y build-essential -> compilar mysqlclient
# - default-mysql-client -> aporta el binario 'mysql' para manage.py dbshell
# - netcat-traditional -> por si tu entrypoint espera a la DB (nc)
# - pkg-config -> requerido por algunos builds
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      default-libmysqlclient-dev \
      default-mysql-client \
      netcat-traditional \
      pkg-config \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# (Opcional) ejecutar como usuario no root
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser

EXPOSE 8000
