from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import logging
import time
from datetime import datetime
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="INMET Weather Data Scraper API",
    description="API para extrair dados meteorológicos do INMET",
    version="1.0.0"
)

# Modelos Pydantic para validação
class WeatherData(BaseModel):
    data: str
    hora: str
    temperatura: Dict[str, Any]
    umidade: Dict[str, Any]
    pto_orvalho: Dict[str, Any]
    pressao: Dict[str, Any]
    vento: Dict[str, Any]
    radiacao: Dict[str, Any]
    chuva: Dict[str, Any]

class WeatherResponse(BaseModel):
    success: bool
    station_id: str
    timestamp: str
    headers: Dict[str, List[str]]
    data: List[WeatherData]
    total_records: int
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool
    error: str
    message: str

def setup_chrome_driver():
    """Configura o driver do Chrome com opções otimizadas"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Configurar service
    service = Service(ChromeDriverManager().install())
    
    return webdriver.Chrome(service=service, options=chrome_options)

def extract_table_data(driver, station_id: str) -> Dict[str, Any]:
    """Extrai dados da tabela meteorológica"""
    try:
        # Aguardar a tabela carregar
        wait = WebDriverWait(driver, 20)
        table = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .table, [class*='table']"))
        )
        
        # Extrair cabeçalhos
        headers = {}
        header_rows = driver.find_elements(By.CSS_SELECTOR, "thead tr, .table-header tr, tr:first-child")
        
        if header_rows:
            # Processar cabeçalhos principais
            main_headers = []
            sub_headers = []
            
            for i, row in enumerate(header_rows):
                cells = row.find_elements(By.CSS_SELECTOR, "th, td")
                if i == 0:  # Primeira linha - cabeçalhos principais
                    main_headers = [cell.text.strip() for cell in cells]
                elif i == 1:  # Segunda linha - subcabeçalhos
                    sub_headers = [cell.text.strip() for cell in cells]
            
            # Estruturar cabeçalhos
            headers = {
                "main_headers": main_headers,
                "sub_headers": sub_headers
            }
        
        # Extrair dados das linhas
        data_rows = []
        body_rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr, .table-body tr")
        
        if not body_rows:
            # Se não encontrar tbody, pegar todas as linhas exceto cabeçalhos
            all_rows = driver.find_elements(By.CSS_SELECTOR, "tr")
            body_rows = all_rows[len(header_rows):] if header_rows else all_rows
        
        for row in body_rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td, th")
            if cells:
                row_data = [cell.text.strip() for cell in cells]
                if any(row_data):  # Só adicionar se não estiver vazia
                    data_rows.append(row_data)
        
        return {
            "headers": headers,
            "data": data_rows,
            "total_records": len(data_rows)
        }
    
    except Exception as e:
        logger.error(f"Erro ao extrair dados da tabela: {str(e)}")
        raise

def process_weather_data(raw_data: Dict[str, Any]) -> List[WeatherData]:
    """Processa os dados brutos em formato estruturado"""
    processed_data = []
    
    try:
        for row in raw_data["data"]:
            if len(row) >= 2:  # Pelo menos data e hora
                # Estruturar dados conforme a tabela INMET
                weather_entry = {
                    "data": row[0] if len(row) > 0 else "",
                    "hora": row[1] if len(row) > 1 else "",
                    "temperatura": {
                        "inst": row[2] if len(row) > 2 else "",
                        "max": row[3] if len(row) > 3 else "",
                        "min": row[4] if len(row) > 4 else ""
                    },
                    "umidade": {
                        "inst": row[5] if len(row) > 5 else "",
                        "max": row[6] if len(row) > 6 else "",
                        "min": row[7] if len(row) > 7 else ""
                    },
                    "pto_orvalho": {
                        "inst": row[8] if len(row) > 8 else "",
                        "max": row[9] if len(row) > 9 else "",
                        "min": row[10] if len(row) > 10 else ""
                    },
                    "pressao": {
                        "inst": row[11] if len(row) > 11 else "",
                        "max": row[12] if len(row) > 12 else "",
                        "min": row[13] if len(row) > 13 else ""
                    },
                    "vento": {
                        "vel": row[14] if len(row) > 14 else "",
                        "dir": row[15] if len(row) > 15 else "",
                        "raj": row[16] if len(row) > 16 else ""
                    },
                    "radiacao": {
                        "kj_m2": row[17] if len(row) > 17 else ""
                    },
                    "chuva": {
                        "mm": row[18] if len(row) > 18 else ""
                    }
                }
                
                processed_data.append(weather_entry)
    
    except Exception as e:
        logger.error(f"Erro ao processar dados: {str(e)}")
    
    return processed_data

@app.get("/")
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "message": "INMET Weather Data Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "/scrape/{station_id}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "INMET Weather Scraper"
    }

@app.get("/scrape/{station_id}")
async def scrape_weather_data(station_id: str):
    """
    Extrai dados meteorológicos de uma estação específica do INMET
    
    Args:
        station_id: ID da estação (ex: A871)
    
    Returns:
        JSON com dados meteorológicos estruturados
    """
    driver = None
    
    try:
        logger.info(f"Iniciando scraping para estação: {station_id}")
        
        # Configurar driver
        driver = setup_chrome_driver()
        
        # Navegar para a página
        url = f"https://tempo.inmet.gov.br/TabelaEstacoes/{station_id}"
        driver.get(url)
        
        # Aguardar carregamento
        time.sleep(5)
        
        # Extrair dados
        raw_data = extract_table_data(driver, station_id)
        
        # Processar dados
        processed_data = process_weather_data(raw_data)
        
        # Preparar resposta
        response = WeatherResponse(
            success=True,
            station_id=station_id,
            timestamp=datetime.now().isoformat(),
            headers=raw_data["headers"],
            data=processed_data,
            total_records=raw_data["total_records"],
            message=f"Dados extraídos com sucesso para estação {station_id}"
        )
        
        logger.info(f"Scraping concluído. {len(processed_data)} registros extraídos.")
        
        return response
        
    except TimeoutException:
        logger.error("Timeout ao aguardar carregamento da página")
        raise HTTPException(
            status_code=408,
            detail="Timeout: Página demorou muito para carregar"
        )
    
    except WebDriverException as e:
        logger.error(f"Erro do WebDriver: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro do navegador: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno do servidor: {str(e)}"
        )
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

@app.get("/scrape/{station_id}/raw")
async def scrape_raw_data(station_id: str):
    """
    Extrai dados brutos da tabela sem processamento
    
    Args:
        station_id: ID da estação (ex: A871)
    
    Returns:
        JSON com dados brutos da tabela
    """
    driver = None
    
    try:
        logger.info(f"Iniciando scraping raw para estação: {station_id}")
        
        # Configurar driver
        driver = setup_chrome_driver()
        
        # Navegar para a página
        url = f"https://tempo.inmet.gov.br/TabelaEstacoes/{station_id}"
        driver.get(url)
        
        # Aguardar carregamento
        time.sleep(5)
        
        # Extrair dados brutos
        raw_data = extract_table_data(driver, station_id)
        
        return {
            "success": True,
            "station_id": station_id,
            "timestamp": datetime.now().isoformat(),
            "raw_data": raw_data
        }
        
    except Exception as e:
        logger.error(f"Erro ao extrair dados brutos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao extrair dados: {str(e)}"
        )
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
