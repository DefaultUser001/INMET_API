"""
API de Web Scraping para dados meteorológicos do INMET
Sistema robusto para extrair dados de estações meteorológicas
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from flask_cors import CORS
import json
from urllib.parse import urlparse
import re

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do Flask
app = Flask(__name__)
CORS(app)

@dataclass
class WeatherData:
    """Classe para estruturar dados meteorológicos"""
    data: str
    hora: str
    temperatura: Dict[str, float]
    umidade: Dict[str, float]
    ponto_orvalho: Dict[str, float]
    pressao: Dict[str, float]
    vento: Dict[str, Any]
    radiacao: float
    chuva: float

class INMETScraper:
    """Classe principal para scraping dos dados do INMET"""
    
    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        self.base_url = "https://tempo.inmet.gov.br/TabelaEstacoes/"
        self.setup_driver()
    
    def setup_driver(self):
        """Configura o driver do Chrome com otimizações"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Otimizações para performance e compatibilidade com containers
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent para evitar detecção
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"Erro ao inicializar driver: {e}")
            raise
    
    def close_driver(self):
        """Fecha o driver de forma segura"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def wait_for_table_load(self, timeout: int = 30) -> bool:
        """Aguarda o carregamento completo da tabela"""
        try:
            # Aguarda a tabela aparecer
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table, .table, .weather-table"))
            )
            
            # Aguarda dados aparecerem nas células
            time.sleep(3)
            
            # Verifica se há dados na tabela
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .table tr")
            return len(rows) > 1  # Mais de uma linha (header + dados)
            
        except TimeoutException:
            logger.warning("Timeout aguardando carregamento da tabela")
            return False
    
    def extract_table_data(self) -> List[Dict]:
        """Extrai dados da tabela com tratamento robusto"""
        try:
            # Múltiplas estratégias para encontrar a tabela
            table_selectors = [
                "table",
                ".table",
                ".weather-table",
                "table.table",
                "div.table-responsive table",
                "#weatherTable",
                ".data-table"
            ]
            
            table = None
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if table:
                        break
                except:
                    continue
            
            if not table:
                logger.error("Tabela não encontrada com nenhum seletor")
                return []
            
            # Extrai headers
            headers = []
            header_selectors = ["thead th", "tr:first-child th", "tr:first-child td"]
            
            for selector in header_selectors:
                try:
                    header_elements = table.find_elements(By.CSS_SELECTOR, selector)
                    if header_elements:
                        headers = [elem.text.strip() for elem in header_elements]
                        break
                except:
                    continue
            
            if not headers:
                logger.warning("Headers não encontrados, usando estrutura padrão")
                headers = ["Data", "Hora", "Temperatura", "Umidade", "Ponto de Orvalho", 
                          "Pressão", "Vento", "Radiação", "Chuva"]
            
            # Extrai dados das linhas
            rows = []
            row_selectors = ["tbody tr", "tr", "tr:not(:first-child)"]
            
            for selector in row_selectors:
                try:
                    row_elements = table.find_elements(By.CSS_SELECTOR, selector)
                    if row_elements:
                        for row in row_elements:
                            cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                            if cells and len(cells) >= 3:  # Pelo menos 3 colunas de dados
                                row_data = [cell.text.strip() for cell in cells]
                                if any(cell for cell in row_data):  # Não vazio
                                    rows.append(row_data)
                        break
                except:
                    continue
            
            # Estrutura os dados
            structured_data = []
            for row in rows:
                if len(row) >= 3:
                    structured_data.append(self.structure_row_data(row, headers))
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da tabela: {e}")
            return []
    
    def structure_row_data(self, row: List[str], headers: List[str]) -> Dict:
        """Estrutura os dados de uma linha conforme a tabela INMET"""
        try:
            # Estrutura básica baseada na tabela fornecida
            data = {}
            
            # Mapeia colunas conforme estrutura do INMET
            for i, value in enumerate(row):
                if i < len(headers):
                    header = headers[i]
                    
                    # Processa diferentes tipos de dados
                    if 'data' in header.lower():
                        data['data'] = value
                    elif 'hora' in header.lower():
                        data['hora'] = value
                    elif 'temperatura' in header.lower():
                        data['temperatura'] = self.parse_temperature_data(value)
                    elif 'umidade' in header.lower():
                        data['umidade'] = self.parse_humidity_data(value)
                    elif 'orvalho' in header.lower():
                        data['ponto_orvalho'] = self.parse_dewpoint_data(value)
                    elif 'pressao' in header.lower():
                        data['pressao'] = self.parse_pressure_data(value)
                    elif 'vento' in header.lower():
                        data['vento'] = self.parse_wind_data(value)
                    elif 'radiacao' in header.lower():
                        data['radiacao'] = self.parse_numeric_value(value)
                    elif 'chuva' in header.lower():
                        data['chuva'] = self.parse_numeric_value(value)
                    else:
                        # Para outras colunas, usa o nome do header
                        data[header.lower().replace(' ', '_')] = value
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao estruturar dados da linha: {e}")
            return {}
    
    def parse_temperature_data(self, value: str) -> Dict[str, float]:
        """Processa dados de temperatura"""
        try:
            # Se for um valor único
            if '/' not in value and ',' not in value:
                return {'atual': float(value.replace(',', '.')) if value and value != '-' else 0.0}
            
            # Se houver múltiplos valores separados por / ou ,
            parts = re.split(r'[/,]', value)
            return {
                'atual': float(parts[0].replace(',', '.')) if len(parts) > 0 and parts[0] != '-' else 0.0,
                'max': float(parts[1].replace(',', '.')) if len(parts) > 1 and parts[1] != '-' else 0.0,
                'min': float(parts[2].replace(',', '.')) if len(parts) > 2 and parts[2] != '-' else 0.0
            }
        except:
            return {'atual': 0.0, 'max': 0.0, 'min': 0.0}
    
    def parse_humidity_data(self, value: str) -> Dict[str, float]:
        """Processa dados de umidade"""
        try:
            if '/' not in value and ',' not in value:
                return {'atual': float(value.replace(',', '.')) if value and value != '-' else 0.0}
            
            parts = re.split(r'[/,]', value)
            return {
                'atual': float(parts[0].replace(',', '.')) if len(parts) > 0 and parts[0] != '-' else 0.0,
                'max': float(parts[1].replace(',', '.')) if len(parts) > 1 and parts[1] != '-' else 0.0,
                'min': float(parts[2].replace(',', '.')) if len(parts) > 2 and parts[2] != '-' else 0.0
            }
        except:
            return {'atual': 0.0, 'max': 0.0, 'min': 0.0}
    
    def parse_dewpoint_data(self, value: str) -> Dict[str, float]:
        """Processa dados de ponto de orvalho"""
        return self.parse_temperature_data(value)
    
    def parse_pressure_data(self, value: str) -> Dict[str, float]:
        """Processa dados de pressão"""
        return self.parse_temperature_data(value)
    
    def parse_wind_data(self, value: str) -> Dict[str, Any]:
        """Processa dados de vento"""
        try:
            # Procura por padrões de velocidade e direção
            wind_match = re.search(r'(\d+\.?\d*)\s*m/s.*?(\d+)°?', value)
            if wind_match:
                return {
                    'velocidade': float(wind_match.group(1)),
                    'direcao': float(wind_match.group(2))
                }
            
            # Se só tem velocidade
            speed_match = re.search(r'(\d+\.?\d*)', value)
            if speed_match:
                return {
                    'velocidade': float(speed_match.group(1)),
                    'direcao': 0.0
                }
            
            return {'velocidade': 0.0, 'direcao': 0.0}
        except:
            return {'velocidade': 0.0, 'direcao': 0.0}
    
    def parse_numeric_value(self, value: str) -> float:
        """Processa valores numéricos simples"""
        try:
            if not value or value == '-':
                return 0.0
            
            # Remove caracteres não numéricos exceto pontos e vírgulas
            clean_value = re.sub(r'[^\d,.\-]', '', value)
            return float(clean_value.replace(',', '.'))
        except:
            return 0.0
    
    def scrape_station(self, station_code: str) -> Dict:
        """Scraping principal de uma estação"""
        try:
            url = f"{self.base_url}{station_code}"
            logger.info(f"Fazendo scraping de: {url}")
            
            self.driver.get(url)
            
            # Aguarda carregamento
            if not self.wait_for_table_load():
                return {
                    'error': 'Timeout - dados não carregaram',
                    'station': station_code,
                    'data': []
                }
            
            # Extrai dados
            data = self.extract_table_data()
            
            return {
                'station': station_code,
                'timestamp': datetime.now().isoformat(),
                'data_count': len(data),
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Erro no scraping da estação {station_code}: {e}")
            return {
                'error': str(e),
                'station': station_code,
                'data': []
            }

# Instância global do scraper
scraper = None

def get_scraper():
    """Obtém instância do scraper (singleton)"""
    global scraper
    if scraper is None:
        scraper = INMETScraper()
    return scraper

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de saúde da API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/station/<station_code>', methods=['GET'])
def get_station_data(station_code: str):
    """Endpoint principal para obter dados de uma estação"""
    try:
        if not station_code:
            return jsonify({'error': 'Código da estação é obrigatório'}), 400
        
        # Valida formato do código da estação
        if not re.match(r'^[A-Z]\d{3}$', station_code):
            return jsonify({'error': 'Formato de código inválido (use A999)'}), 400
        
        scraper = get_scraper()
        result = scraper.scrape_station(station_code)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro no endpoint da estação: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stations', methods=['POST'])
def get_multiple_stations():
    """Endpoint para obter dados de múltiplas estações"""
    try:
        data = request.get_json()
        
        if not data or 'stations' not in data:
            return jsonify({'error': 'Lista de estações é obrigatória'}), 400
        
        stations = data['stations']
        if not isinstance(stations, list) or len(stations) == 0:
            return jsonify({'error': 'Lista de estações deve ser um array não vazio'}), 400
        
        scraper = get_scraper()
        results = []
        
        for station_code in stations:
            if not re.match(r'^[A-Z]\d{3}$', station_code):
                results.append({
                    'station': station_code,
                    'error': 'Formato de código inválido'
                })
                continue
            
            result = scraper.scrape_station(station_code)
            results.append(result)
            
            # Delay entre requisições para evitar sobrecarga
            time.sleep(1)
        
        return jsonify({
            'total_stations': len(stations),
            'processed': len(results),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Erro no endpoint de múltiplas estações: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """Documentação da API"""
    docs = {
        'title': 'API de Dados Meteorológicos INMET',
        'version': '1.0.0',
        'description': 'API para extrair dados meteorológicos do INMET via web scraping',
        'base_url': request.host_url,
        'endpoints': {
            'GET /health': {
                'description': 'Verifica saúde da API',
                'response': 'Status da API'
            },
            'GET /api/station/<codigo>': {
                'description': 'Obter dados de uma estação específica',
                'parameters': {
                    'codigo': 'Código da estação (formato A999, ex: A871)'
                },
                'example': '/api/station/A871'
            },
            'POST /api/stations': {
                'description': 'Obter dados de múltiplas estações',
                'body': {
                    'stations': ['A871', 'A652', 'A301']
                }
            }
        },
        'data_structure': {
            'station': 'Código da estação',
            'timestamp': 'Timestamp da extração',
            'data_count': 'Número de registros extraídos',
            'data': [
                {
                    'data': 'Data do registro',
                    'hora': 'Hora do registro',
                    'temperatura': {
                        'atual': 'Temperatura atual',
                        'max': 'Temperatura máxima',
                        'min': 'Temperatura mínima'
                    },
                    'umidade': {
                        'atual': 'Umidade atual',
                        'max': 'Umidade máxima',
                        'min': 'Umidade mínima'
                    },
                    'ponto_orvalho': 'Ponto de orvalho',
                    'pressao': 'Pressão atmosférica',
                    'vento': {
                        'velocidade': 'Velocidade do vento',
                        'direcao': 'Direção do vento'
                    },
                    'radiacao': 'Radiação solar',
                    'chuva': 'Precipitação'
                }
            ]
        }
    }
    
    return jsonify(docs)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
