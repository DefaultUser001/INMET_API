const express = require('express');
const puppeteer = require('puppeteer');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const NodeCache = require('node-cache');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Cache com TTL de 5 minutos (300 segundos)
const cache = new NodeCache({ stdTTL: 300 });

// Middlewares de segurança
app.use(helmet());
app.use(cors());
app.use(express.json());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutos
  max: 100, // máximo 100 requests por IP por janela
  message: {
    error: 'Muitas requisições, tente novamente em 15 minutos',
    code: 429
  }
});

app.use('/api/', limiter);

// Função para extrair dados da tabela
async function scrapeWeatherData(stationCode) {
  const cacheKey = `weather_${stationCode}`;
  
  // Verifica se os dados estão em cache
  const cachedData = cache.get(cacheKey);
  if (cachedData) {
    return cachedData;
  }

  let browser;
  try {
    browser = await puppeteer.launch({
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ],
      headless: 'new'
    });

    const page = await browser.newPage();
    
    // Configura viewport e headers
    await page.setViewport({ width: 1920, height: 1080 });
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    
    const url = `https://tempo.inmet.gov.br/TabelaEstacoes/${stationCode}`;
    
    console.log(`Acessando: ${url}`);
    
    // Navega para a página
    await page.goto(url, { 
      waitUntil: 'networkidle2', 
      timeout: 30000 
    });

    // Aguarda a tabela carregar
    await page.waitForSelector('table', { timeout: 20000 });
    
    // Extrai os dados da tabela
    const weatherData = await page.evaluate(() => {
      const tables = document.querySelectorAll('table');
      let targetTable = null;
      
      // Procura pela tabela com dados meteorológicos
      for (let table of tables) {
        const headers = table.querySelectorAll('th');
        if (headers.length > 5) { // Tabela com múltiplas colunas
          targetTable = table;
          break;
        }
      }
      
      if (!targetTable) {
        throw new Error('Tabela de dados meteorológicos não encontrada');
      }
      
      const result = {
        headers: [],
        subHeaders: [],
        data: [],
        metadata: {
          extractedAt: new Date().toISOString(),
          stationCode: null,
          stationName: null
        }
      };
      
      // Extrai informações da estação
      const pageTitle = document.title;
      const stationInfo = document.querySelector('.station-info') || document.querySelector('h1, h2, h3');
      if (stationInfo) {
        result.metadata.stationName = stationInfo.textContent.trim();
      }
      
      // Extrai headers principais
      const headerRows = targetTable.querySelectorAll('thead tr, tr');
      let headerRowIndex = 0;
      let subHeaderRowIndex = 1;
      
      // Procura pelas linhas de header
      for (let i = 0; i < headerRows.length; i++) {
        const row = headerRows[i];
        const cells = row.querySelectorAll('th, td');
        
        if (cells.length > 5 && cells[0].textContent.trim() !== '') {
          if (result.headers.length === 0) {
            headerRowIndex = i;
          } else if (result.subHeaders.length === 0) {
            subHeaderRowIndex = i;
            break;
          }
        }
      }
      
      // Extrai headers principais
      if (headerRows[headerRowIndex]) {
        const headerCells = headerRows[headerRowIndex].querySelectorAll('th, td');
        headerCells.forEach(cell => {
          result.headers.push(cell.textContent.trim());
        });
      }
      
      // Extrai sub-headers
      if (headerRows[subHeaderRowIndex] && subHeaderRowIndex !== headerRowIndex) {
        const subHeaderCells = headerRows[subHeaderRowIndex].querySelectorAll('th, td');
        subHeaderCells.forEach(cell => {
          result.subHeaders.push(cell.textContent.trim());
        });
      }
      
      // Extrai dados das linhas
      const dataRows = targetTable.querySelectorAll('tbody tr, tr');
      
      for (let row of dataRows) {
        const cells = row.querySelectorAll('td, th');
        
        if (cells.length > 5) {
          const rowData = {};
          
          cells.forEach((cell, index) => {
            const headerName = result.headers[index] || `col_${index}`;
            const subHeaderName = result.subHeaders[index] || '';
            
            let finalHeaderName = headerName;
            if (subHeaderName && subHeaderName !== headerName) {
              finalHeaderName = `${headerName}_${subHeaderName}`;
            }
            
            let cellValue = cell.textContent.trim();
            
            // Tenta converter números
            if (cellValue && !isNaN(cellValue) && cellValue !== '') {
              cellValue = parseFloat(cellValue);
            }
            
            rowData[finalHeaderName] = cellValue;
          });
          
          // Apenas adiciona se a linha contém dados válidos
          if (Object.values(rowData).some(val => val !== '' && val !== null && val !== undefined)) {
            result.data.push(rowData);
          }
        }
      }
      
      return result;
    });
    
    // Armazena no cache
    cache.set(cacheKey, weatherData);
    
    return weatherData;
    
  } catch (error) {
    console.error('Erro no scraping:', error);
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Rotas da API
app.get('/', (req, res) => {
  res.json({
    message: 'API de Web Scraping - Dados Meteorológicos INMET',
    version: '1.0.0',
    endpoints: {
      '/api/weather/:stationCode': 'Obtém dados meteorológicos de uma estação',
      '/api/health': 'Verifica status da API',
      '/api/cache/clear': 'Limpa o cache (apenas para desenvolvimento)'
    },
    usage: {
      example: '/api/weather/A871',
      description: 'Substitua :stationCode pelo código da estação desejada'
    }
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    cache: {
      keys: cache.keys().length,
      stats: cache.getStats()
    }
  });
});

app.get('/api/weather/:stationCode', async (req, res) => {
  try {
    const { stationCode } = req.params;
    
    if (!stationCode || stationCode.length < 2) {
      return res.status(400).json({
        error: 'Código da estação inválido',
        code: 400
      });
    }
    
    console.log(`Requisição para estação: ${stationCode}`);
    
    const weatherData = await scrapeWeatherData(stationCode);
    
    res.json({
      success: true,
      stationCode,
      data: weatherData,
      cached: cache.has(`weather_${stationCode}`)
    });
    
  } catch (error) {
    console.error('Erro na API:', error);
    
    res.status(500).json({
      error: 'Erro ao extrair dados meteorológicos',
      message: error.message,
      code: 500
    });
  }
});

// Endpoint para limpar cache (apenas desenvolvimento)
app.delete('/api/cache/clear', (req, res) => {
  if (process.env.NODE_ENV === 'production') {
    return res.status(403).json({
      error: 'Operação não permitida em produção',
      code: 403
    });
  }
  
  cache.flushAll();
  res.json({
    message: 'Cache limpo com sucesso',
    timestamp: new Date().toISOString()
  });
});

// Middleware de erro global
app.use((err, req, res, next) => {
  console.error('Erro global:', err);
  res.status(500).json({
    error: 'Erro interno do servidor',
    code: 500
  });
});

// Middleware para rotas não encontradas
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Rota não encontrada',
    code: 404
  });
});

// Inicializa o servidor
app.listen(PORT, () => {
  console.log(`🚀 Servidor rodando na porta ${PORT}`);
  console.log(`📡 API disponível em: http://localhost:${PORT}`);
  console.log(`🔍 Exemplo de uso: http://localhost:${PORT}/api/weather/A871`);
});
