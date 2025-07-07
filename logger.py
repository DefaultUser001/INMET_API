import logging
from pathlib import Path

# Garante que diretório de logs existe
Path("logs").mkdir(exist_ok=True)

log_file = "logs/access.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_access(ip: str, route: str, status: int):
    logging.info(f"{ip} - {route} - Status: {status}")
