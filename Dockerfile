# Use imagem oficial do Python
FROM python:3.11-slim

# Variáveis de ambiente para comportamento do Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Define o diretório de trabalho no container
WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o código-fonte da API e do dashboard
COPY ./app ./app
COPY ./dashboard ./dashboard

# Expõe a porta padrão da API
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
