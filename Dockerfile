# === File: Dockerfile ===

# 1. Usar una imagen oficial de Python como base
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de requerimientos e instalarlos
# Se copia primero para aprovechar el caché de Docker si no cambia
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 4. Copiar el resto del código de la aplicación
COPY . .

# 5. Exponer el puerto en el que FastAPI se ejecutará (ej. 8000)
EXPOSE 8000

# 6. El comando para iniciar la aplicación cuando el contenedor arranque
# Se usa uvicorn, el servidor estándar para FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]