# === File: Dockerfile ===

# 1. Usar una imagen oficial de Python como base
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de requerimientos e instalarlos
# Copy first to take advantage of Docker cache if it doesn't change
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 4. Copy the rest of the application code
COPY . .

# 5. Expose the port where FastAPI will run (e.g. 8000)
EXPOSE 8000

# 6. Command to start the application when the container starts
# Uses uvicorn, the standard server for FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]