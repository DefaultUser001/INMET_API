from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.scraper import scrape_inmet_data
from app.config import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
import uvicorn

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="INMET Web Scraper API",
    description="API para extrair dados da estação A871 do INMET",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limiting e segurança CORS
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Verificação de API Key via header
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Chave de API inválida.")

@app.get("/dados")
@limiter.limit("5/minute")  # 5 requisições por minuto por IP
async def get_dados(api_key: str = Depends(verify_api_key)):
    try:
        data = scrape_inmet_data()
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
