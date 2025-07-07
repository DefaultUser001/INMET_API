from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import pandas as pd
import time

def obter_inmet(uf='RS', estacao='A801', inicio='01/01/2021', fim='31/12/2021'):
    url = f'https://tempo.inmet.gov.br/TabelaEstacoes/{uf.upper()}'

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.binary_location = "/usr/bin/google-chrome"

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)

        # Seleciona estação
        Select(driver.find_element('xpath', "//select[@class='estacao']")).select_by_value(estacao)

        # Insere datas
        de = driver.find_element('id', 'dataInicial')
        de.clear(); de.send_keys(inicio)

        ate = driver.find_element('id', 'dataFinal')
        ate.clear(); ate.send_keys(fim)

        # Clica em "Enviar"
        driver.find_element('id', 'btnEnviar').click()

        time.sleep(5)  # aguarda carregamento

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tabela = soup.find('table', {'class': 'tabela_dados'})
        if tabela is None:
            raise ValueError("Tabela não encontrada. Verifique se a estação ou data estão corretas.")

        df = pd.read_html(str(tabela))[0]
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        return df.to_dict(orient='records')

    finally:
        driver.quit()
