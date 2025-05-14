# Usar una imagen base de Python. Ajusta la versión según los requisitos de Odoo 18.
# Python 3.10 o 3.11 suelen ser buenas opciones para versiones recientes de Odoo.
FROM python:3.11-slim

LABEL maintainer="sinapxi <tu_email@example.com>" \
      org.opencontainers.image.source="https://github.com/sinapxi/odoo-arizon"

# Variables de entorno para optimizar Python y logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Variables para la configuración regional y codificación, importantes para Odoo
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Instalar dependencias del sistema operativo necesarias para Odoo y python-ldap
# Actualizar lista de paquetes e instalar dependencias en un solo RUN para reducir capas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    # Dependencias para python-ldap
    libldap2-dev \
    libsasl2-dev \
    # Dependencias comunes para Odoo y otras librerías de Python
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libffi-dev \
    zlib1g-dev \
    libpq-dev \
    # Git es útil para algunas dependencias o si necesitas obtener algo de repositorios
    git \
    # Wkhtmltopdf para la generación de reportes PDF en Odoo
    # Nota: La instalación de wkhtmltopdf puede ser más compleja para obtener la versión correcta
    # parcheada para Odoo (con qt). Esta es una instalación básica.
    # Es posible que necesites descargar un .deb específico si tienes problemas con los PDFs.
    wkhtmltopdf \
    # Limpiar el caché de apt para reducir el tamaño de la imagen
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de requerimientos primero para aprovechar el caché de Docker
# Si requirements.txt no cambia, esta capa no se reconstruirá innecesariamente
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación al directorio de trabajo
COPY . .

# Asegurar que odoo-bin sea ejecutable (Git debería preservar esto, pero por si acaso)
RUN chmod +x odoo-bin

# Crear un usuario no root para ejecutar Odoo (mejora la seguridad)
# RUN useradd --create-home --shell /bin/bash odoo
# WORKDIR /home/odoo/app # Si se usa un usuario no root, ajustar el WORKDIR y los COPY
# USER odoo
# Por simplicidad para empezar, lo ejecutaremos como root. Puedes habilitar esto más tarde.

# Volumen para el filestore de Odoo (Railway lo manejará a través de su configuración de volúmenes)
# No necesitas definirlo aquí si ya lo tienes en Railway, pero es informativo.
# VOLUME ["/var/lib/odoo"]

# Exponer el puerto en el que Odoo escuchará (Railway lo sobreescribirá con $PORT)
EXPOSE 8069

# Comando de inicio para Odoo
# Usa la variable de entorno $PORT que Railway proporcionará.
# CMD ["/app/odoo-bin", "--config=/app/odoo-arizon/odoo.conf", "--http-port=$PORT", "--http-interface=0.0.0.0", "--without-demo=all", "--workers=2", "--logfile=/dev/stdout"]

# Comando temporal para depuración avanzada de odoo-bin
CMD ["sh", "-c", "echo 'Contenido de /app:'; ls -l /app; echo '---'; echo 'Detalles de /app/odoo-bin:'; ls -l /app/odoo-bin; echo '---'; echo 'Primeras líneas de /app/odoo-bin (con cat -A para ver caracteres especiales):'; head -n 5 /app/odoo-bin | cat -A; echo '---'; echo 'Tipo de archivo de /app/odoo-bin:'; file /app/odoo-bin; echo '---'; echo 'Intentando ejecutar /app/odoo-bin --version directamente:'; /app/odoo-bin --version; echo '---'; echo 'Intentando ejecutar con python3 explícito:'; python3 /app/odoo-bin --version; echo '---'; echo 'PATH del sistema:'; echo $PATH; echo '---'; echo 'Durmiendo indefinidamente para mantener el contenedor activo y revisar logs.'; sleep infinity"] 