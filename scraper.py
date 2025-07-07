import requests
from bs4 import BeautifulSoup

def scrape_inmet_data():
    url = "https://tempo.inmet.gov.br/TabelaEstacoes/A871"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; WebScraper/1.0; +https://seusite.com)"
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("Tabela não encontrada na página.")

    headers = [th.text.strip() for th in table.find_all("th")]
    data = []

    for row in table.find_all("tr")[1:]:
        cols = [td.text.strip() for td in row.find_all("td")]
        if len(cols) == len(headers):
            entry = dict(zip(headers, cols))
            data.append(entry)

    return data
