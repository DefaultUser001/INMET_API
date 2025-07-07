from flask import Flask, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

URL = "https://tempo.inmet.gov.br/TabelaEstacoes/A871"
TABLE_CLASS = "ui blue celled striped unstackable table"

@app.route('/inmet', methods=['GET'])
def get_weather_data():
    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find("table", {"class": TABLE_CLASS})

    headers = []
    data = []

    if not table:
        return jsonify({"error": "Tabela não encontrada"}), 404

    rows = table.find_all("tr")

    # Extrai cabeçalhos com subcabeçalhos combinados
    header_rows = rows[:2]
    cols1 = [col.get_text(strip=True) for col in header_rows[0].find_all(['th'])]
    cols2 = [col.get_text(strip=True) for col in header_rows[1].find_all(['th'])]

    # Combina os cabeçalhos principais com os secundários
    i = 0
    for c1 in cols1:
        colspan = header_rows[0].find_all(['th'])[i].get('colspan')
        if colspan:
            for j in range(int(colspan)):
                headers.append(f"{c1} - {cols2.pop(0)}")
        else:
            headers.append(c1)
        i += 1

    # Extrai os dados
    for row in rows[2:]:
        cols = [col.get_text(strip=True).replace(",", ".") for col in row.find_all("td")]
        if cols:
            entry = dict(zip(headers, cols))
            data.append(entry)

    return jsonify(data)

@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
