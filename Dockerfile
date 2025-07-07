FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg2 \
    chromium-driver chromium \
    && apt-get clean

# Instala Python libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da API
COPY . /app
WORKDIR /app

EXPOSE 8000
CMD ["python", "app.py"]
