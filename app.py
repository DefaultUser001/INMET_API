from flask import Flask, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
CORS(app)

URL = "https://tempo.inmet.gov.br/TabelaEstacoes/A871"
TABLE_CLASS = "ui blue celled striped unstackable table"

def get_table_with_selenium():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)
    driver.get(URL)

    try:
        # Espera até que a tabela seja carregada no DOM (máx 15 segundos)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ui.blue.celled.striped.unstackable.table"))
        )
        html = driver.page_source
    except Exception as e:
        driver.quit()
        return None, f"Erro ao esperar tabela: {str(e)}"

    driver.quit()
    return html, None

@app.route('/inmet', methods=['GET'])
def get_weather_data():
    html, error = get_table_with_selenium()
    if error:
        return jsonify({"error": error}), 500

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find("table", {"class": TABLE_CLASS})
    
    if not table:
        return jsonify({"error": "Tabela não encontrada"}), 404

    rows = table.find_all("tr")
    header_rows = rows[:2]
    data = []

    # Extrai cabeçalhos combinando títulos e subtítulos
    cols1 = [col.get_text(strip=True) for col in header_rows[0].find_all(['th'])]
    cols2 = [col.get_text(strip=True) for col in header_rows[1].find_all(['th'])]

    headers = []
    i = 0
    for c1 in cols1:
        colspan = header_rows[0].find_all(['th'])[i].get('colspan')
        if colspan:
            for j in range(int(colspan)):
                headers.append(f"{c1} - {cols2.pop(0)}")
        else:
            headers.append(c1)
        i += 1

    for row in rows[2:]:
        cols = [col.get_text(strip=True).replace(",", ".") for col in row.find_all("td")]
        if cols:
            entry = dict(zip(headers, cols))
            data.append(entry)

    return jsonify(data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
