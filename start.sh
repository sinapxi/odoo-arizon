#!/bin/bash

# Establecer el puerto por defecto si no está definido
export PORT=${PORT:-8069}
echo "Starting Odoo on main port $PORT (longpolling handled by http port due to proxy_mode, attempting to disable separate evented service)"

# Configurar variables de entorno adicionales si es necesario
export PYTHONUNBUFFERED=1

# Iniciar Odoo con los parámetros correctos
# Reemplaza la ruta a odoo-bin y odoo.conf según tu estructura
cd /app
exec python3 /app/odoo-bin \
    -c /app/odoo-arizon/odoo.conf \
    --http-port=$PORT \
    --db_host=${DB_HOST} \
    --db_port=${PGPORT} \
    --db_user=${PGUSER} \
    --db_password=${PGPASSWORD} \
    --logfile=/dev/stdout \
    --without-demo=all \
    --no-evented-longpolling 