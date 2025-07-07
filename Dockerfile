# Usa imagem leve do Python
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos necessários
COPY . /app

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe porta
EXPOSE 8000

# Executa a aplicação
CMD ["python", "app.py"]
