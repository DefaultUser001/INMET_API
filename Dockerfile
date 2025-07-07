# Imagem base com Python + Chrome + Chromium Driver
FROM python:3.11-slim

# Evita prompts de instalação
ENV DEBIAN_FRONTEND=noninteractive

# Atualiza pacotes e instala dependências do Chrome + Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    fonts-liberation \
    xdg-utils \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instala o Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Define o path do Chrome
ENV CHROME_BIN=/usr/bin/google-chrome

# Instala Chromedriver compatível
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1) && \
    DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# Cria diretório da aplicação
WORKDIR /app

# Copia os arquivos da aplicação
COPY . .

# Instala dependências do Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Expõe a porta padrão
EXPOSE 8000

# Comando de inicialização (usa gunicorn)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
