from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import logging
import os
from datetime import datetime
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class INMETScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """Configurar o driver do Selenium"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Driver Chrome configurado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao configurar driver: {e}")
            raise
            
    def scrape_station_data(self, station_code):
        """Fazer scraping dos dados da estação meteorológica"""
        if not self.driver:
            self.setup_driver()
            
        url = f"https://tempo.inmet.gov.br/TabelaEstacoes/{station_code}"
        
        try:
            logger.info(f"Acessando URL: {url}")
            self.driver.get(url)
            
            # Aguardar o carregamento da página
            wait = WebDriverWait(self.driver, 20)
            
            # Aguardar a tabela carregar (pode precisar ajustar o seletor)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(3)  # Aguardar carregamento completo
            
            # Obter o HTML da página
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Procurar pela tabela de dados
            table = soup.find('table')
            if not table:
                logger.error("Tabela não encontrada na página")
                return None
                
            return self.parse_table_data(table)
            
        except Exception as e:
            logger.error(f"Erro ao fazer scraping: {e}")
            return None
            
    def parse_table_data(self, table):
        """Fazer parsing dos dados da tabela"""
        try:
            data = []
            rows = table.find_all('tr')
            
            if len(rows) < 2:
                logger.error("Tabela sem dados suficientes")
                return None
                
            # Obter cabeçalhos
            headers = []
            header_row = rows[0]
            for th in header_row.find_all(['th', 'td']):
                headers.append(th.get_text(strip=True))
                
            logger.info(f"Cabeçalhos encontrados: {headers}")
            
            # Processar dados
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= len(headers):
                    row_data = {}
                    for i, cell in enumerate(cells[:len(headers)]):
                        if i < len(headers):
                            row_data[headers[i]] = cell.get_text(strip=True)
                    
                    # Estruturar dados conforme formato esperado
                    if self.is_valid_data_row(row_data):
                        formatted_data = self.format_weather_data(row_data)
                        if formatted_data:
                            data.append(formatted_data)
                            
            logger.info(f"Total de registros processados: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Erro ao fazer parsing da tabela: {e}")
            return None
            
    def is_valid_data_row(self, row_data):
        """Verificar se a linha contém dados válidos"""
        # Verificar se contém dados essenciais
        required_keys = ['Data', 'Hora']
        return any(key in row_data for key in required_keys)
        
    def format_weather_data(self, row_data):
        """Formatar dados meteorológicos"""
        try:
            formatted = {
                'timestamp': datetime.now().isoformat(),
                'data': row_data.get('Data', ''),
                'hora': row_data.get('Hora', ''),
                'temperatura': {
                    'instantanea': self.safe_float(row_data.get('Inst.', '')),
                    'maxima': self.safe_float(row_data.get('Máx.', '')),
                    'minima': self.safe_float(row_data.get('Mín.', ''))
                },
                'umidade': {
                    'instantanea': self.safe_float(row_data.get('Inst.', '')),
                    'maxima': self.safe_float(row_data.get('Máx.', '')),
                    'minima': self.safe_float(row_data.get('Mín.', ''))
                },
                'ponto_orvalho': {
                    'instantaneo': self.safe_float(row_data.get('Inst.', '')),
                    'maximo': self.safe_float(row_data.get('Máx.', '')),
                    'minimo': self.safe_float(row_data.get('Mín.', ''))
                },
                'pressao': {
                    'instantanea': self.safe_float(row_data.get('Inst.', '')),
                    'maxima': self.safe_float(row_data.get('Máx.', '')),
                    'minima': self.safe_float(row_data.get('Mín.', ''))
                },
                'vento': {
                    'velocidade': self.safe_float(row_data.get('Vel. (m/s)', '')),
                    'direcao': self.safe_float(row_data.get('Dir. (°)', '')),
                    'rajada': self.safe_float(row_data.get('Raj. (m/s)', ''))
                },
                'radiacao': self.safe_float(row_data.get('Kj/m²', '')),
                'chuva': self.safe_float(row_data.get('mm', ''))
            }
            
            return formatted
            
        except Exception as e:
            logger.error(f"Erro ao formatar dados: {e}")
            return None
            
    def safe_float(self, value):
        """Converter valor para float de forma segura"""
        try:
            if value and value.strip():
                return float(value.replace(',', '.'))
            return None
        except:
            return None
            
    def close_driver(self):
        """Fechar o driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

# Instância global do scraper
scraper = INMETScraper()

@app.route('/')
def home():
    """Página inicial da API"""
    return jsonify({
        'message': 'API de Web Scraping INMET',
        'version': '1.0.0',
        'endpoints': {
            '/station/<station_code>': 'GET - Obter dados da estação meteorológica',
            '/health': 'GET - Verificar saúde da API'
        }
    })

@app.route('/health')
def health_check():
    """Verificar saúde da API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/station/<station_code>')
def get_station_data(station_code):
    """Obter dados da estação meteorológica"""
    try:
        logger.info(f"Solicitação para estação: {station_code}")
        
        # Fazer scraping dos dados
        data = scraper.scrape_station_data(station_code)
        
        if data is None:
            return jsonify({
                'error': 'Não foi possível obter os dados da estação',
                'station_code': station_code
            }), 500
            
        return jsonify({
            'station_code': station_code,
            'data_count': len(data),
            'last_updated': datetime.now().isoformat(),
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Erro na rota /station/{station_code}: {e}")
        return jsonify({
            'error': 'Erro interno do servidor',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
