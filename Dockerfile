FROM python:3.11-slim

WORKDIR /app

# Instalar curl para healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . .

# Crear directorio de datos
RUN mkdir -p data

# Variables de entorno
ENV FLASK_DEBUG=False
ENV SECRET_KEY=cambiar-esta-clave-en-produccion
ENV GUNICORN_WORKERS=4

# Puerto
EXPOSE 5000

# Inicializar BD y ejecutar con configuracion optimizada para confiabilidad
CMD python -c "from models import init_database; init_database()" && \
    gunicorn --bind 0.0.0.0:5000 \
             --workers ${GUNICORN_WORKERS:-4} \
             --threads 2 \
             --worker-class gthread \
             --timeout 120 \
             --graceful-timeout 30 \
             --keep-alive 5 \
             --max-requests 1000 \
             --max-requests-jitter 50 \
             --preload \
             --capture-output \
             --access-logfile - \
             --error-logfile - \
             --log-level info \
             app:app
