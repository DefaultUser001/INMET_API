from flask import Flask, jsonify, request
from scraper import obter_inmet

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'mensagem': 'API INMET ativa.'})

@app.route('/api/inmet', methods=['GET'])
def api_inmet():
    uf = request.args.get('uf', 'RS')
    estacao = request.args.get('estacao', 'A801')
    inicio = request.args.get('inicio', '01/01/2021')
    fim = request.args.get('fim', '31/12/2021')

    try:
        dados = obter_inmet(uf, estacao, inicio, fim)
        return jsonify(dados)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
