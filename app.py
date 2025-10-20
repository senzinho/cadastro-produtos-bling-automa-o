from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
from datetime import datetime
import base64

app = Flask(__name__)
CORS(app)  # Permite requisições do front-end

# ==================== CONFIGURAÇÕES ====================
BLING_API_URL = "https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id=9a332428b534dcb305d81f6e0a464be5daa1d1cf&state=7f57fc7e31113b6c4b53777abd4eadd8"
BLING_API_KEY = "9a332428b534dcb305d81f6e0a464be5daa1d1cf"  # ⚠️ SUBSTITUA pelo seu token do Bling

# ==================== FUNÇÕES AUXILIARES ====================

def converter_para_formato_bling(produto):
    """
    Converte os dados do formulário para o formato esperado pela API do Bling
    
    Args:
        produto (dict): Dados do produto vindos do front-end
        
    Returns:
        dict: Dados formatados para o Bling
    """
    
    # Mapeamento de campos
    produto_bling = {
        "nome": produto.get('descricao', ''),  # Descrição vira nome no Bling
        "codigo": produto.get('codigo', ''),
        "preco": float(produto.get('preco', 0)),
        "tipo": "P",  # P = Produto
        "situacao": "A" if produto.get('situacao') == "Ativo" else "I",
        "formato": "S",  # S = Simples
        "descricaoCurta": produto.get('descricaoCurta', ''),
        "descricaoComplementar": produto.get('descricaoComplementar', ''),
        "unidade": produto.get('unidade', 'UN'),
        "marca": produto.get('marca', ''),
    }
    
    # Peso e dimensões (apenas se fornecidos)
    if produto.get('pesoLiquido'):
        produto_bling['pesoLiquido'] = float(produto.get('pesoLiquido'))
    
    if produto.get('pesoBruto'):
        produto_bling['pesoBruto'] = float(produto.get('pesoBruto'))
    
    if produto.get('volumes'):
        produto_bling['volumes'] = int(produto.get('volumes', 1))
    
    if produto.get('itensPorCaixa'):
        produto_bling['itensPorCaixa'] = float(produto.get('itensPorCaixa', 0))
    
    # Códigos de barras
    if produto.get('gtinEan'):
        produto_bling['gtin'] = produto.get('gtinEan')
    
    if produto.get('gtinEanEmbalagem'):
        produto_bling['gtinEmbalagem'] = produto.get('gtinEanEmbalagem')
    
    # Informações fiscais
    if produto.get('ncm'):
        produto_bling['ncm'] = produto.get('ncm')
    
    if produto.get('origem'):
        produto_bling['origem'] = int(produto.get('origem', 0))
    
    if produto.get('cest'):
        produto_bling['cest'] = produto.get('cest')
    
    # Tipo de produção
    tipo_producao_map = {
        'Própria': 'P',
        'Terceiros': 'T'
    }
    if produto.get('tipoProducao'):
        produto_bling['tipoProducao'] = tipo_producao_map.get(produto.get('tipoProducao'), 'P')
    
    # Condição do produto
    condicao_map = {
        'NOVO': 0,
        'USADO': 2
    }
    if produto.get('condicao'):
        produto_bling['condicao'] = condicao_map.get(produto.get('condicao'), 0)
    
    # Frete grátis
    if produto.get('freteGratis'):
        produto_bling['freteGratis'] = produto.get('freteGratis') == 'SIM'
    
    # Estoque
    estoque_data = {}
    if produto.get('estoqueMinimo'):
        estoque_data['minimo'] = float(produto.get('estoqueMinimo', 0))
    if produto.get('estoqueMaximo'):
        estoque_data['maximo'] = float(produto.get('estoqueMaximo', 0))
    if produto.get('localizacao'):
        estoque_data['localizacao'] = produto.get('localizacao')
    
    if estoque_data:
        produto_bling['estoque'] = estoque_data
    
    # Dimensões
    dimensoes_data = {}
    if produto.get('largura'):
        dimensoes_data['largura'] = float(produto.get('largura'))
    if produto.get('altura'):
        dimensoes_data['altura'] = float(produto.get('altura'))
    if produto.get('profundidade'):
        dimensoes_data['profundidade'] = float(produto.get('profundidade'))
    
    # Unidade de medida: 1 = Centímetros, 2 = Metros
    unidade_medida_map = {
        'Centímetro': 1,
        'Metro': 2
    }
    if produto.get('unidadeMedida'):
        dimensoes_data['unidadeMedida'] = unidade_medida_map.get(produto.get('unidadeMedida'), 1)
    
    if dimensoes_data:
        produto_bling['dimensoes'] = dimensoes_data
    
    # Imagens (se existirem URLs)
    if produto.get('imagens') and isinstance(produto.get('imagens'), list):
        imagens_urls = [img for img in produto.get('imagens') if img and not img.startswith('data:')]
        if imagens_urls:
            produto_bling['imagens'] = [
                {
                    "tipo": "E",  # E = Externa
                    "url": url
                } for url in imagens_urls[:8]  # Máximo 8 imagens
            ]
    
    # Observações
    if produto.get('observacoes'):
        produto_bling['observacoes'] = produto.get('observacoes')
    
    return produto_bling

def criar_produto_bling(produto_data):
    """
    Envia um produto para a API do Bling
    
    Args:
        produto_data (dict): Dados do produto no formato do front-end
        
    Returns:
        dict: Resultado da requisição com status e resposta
    """
    
    # Converte para o formato do Bling
    produto_bling = converter_para_formato_bling(produto_data)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BLING_API_KEY}"
    }
    
    try:
        # Faz a requisição POST para criar o produto
        response = requests.post(
            BLING_API_URL,
            headers=headers,
            json=produto_bling,
            timeout=30
        )
        
        # Registra no console para debug
        print(f"[{datetime.now()}] Produto: {produto_bling.get('nome', 'N/A')} - Status: {response.status_code}")
        
        # Se houver erro, mostra a resposta
        if response.status_code not in [200, 201]:
            print(f"   Erro: {response.text}")
        
        return {
            "status_code": response.status_code,
            "response": response.json() if response.text else {},
            "success": response.status_code in [200, 201],
            "timestamp": datetime.now().isoformat()
        }
        
    except requests.exceptions.Timeout:
        return {
            "status_code": 408,
            "error": "Timeout: A API do Bling demorou muito para responder",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": 500,
            "error": f"Erro de conexão: {str(e)}",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status_code": 500,
            "error": f"Erro inesperado: {str(e)}",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }

# ==================== ROTAS/ENDPOINTS ====================

@app.route('/', methods=['GET'])
def index():
    """
    Página inicial com documentação básica da API
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Cadastro Bling</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 900px; 
                margin: 50px auto; 
                padding: 20px;
                background: #0f1419;
                color: #20B2AA;
            }
            h1 { color: #20B2AA; }
            h2 { color: #5F9EA0; margin-top: 30px; }
            .endpoint { 
                background: #161f27; 
                padding: 15px; 
                margin: 10px 0; 
                border-left: 4px solid #20B2AA;
                border-radius: 5px;
            }
            code { 
                background: #0f1419; 
                padding: 2px 6px; 
                border-radius: 3px;
                color: #20B2AA;
            }
            .method { 
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: bold;
                margin-right: 10px;
            }
            .post { background: #20B2AA; color: #000; }
            .get { background: transparent; border: 2px solid #20B2AA; color: #20B2AA; }
        </style>
    </head>
    <body>
        <h1>🚀 API de Cadastro em Massa - Bling</h1>
        <p>Sistema para cadastrar produtos no Bling via API v3</p>
        
        <h2>📡 Endpoints Disponíveis:</h2>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/cadastrar-produto</strong>
            <p>Cadastra um único produto no Bling</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/cadastrar-produtos-massa</strong>
            <p>Cadastra múltiplos produtos de uma vez</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/exemplo-produto</strong>
            <p>Retorna um exemplo de estrutura JSON de produto</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/testar-conexao</strong>
            <p>Testa a conexão com a API do Bling</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/status</strong>
            <p>Verifica se a API está funcionando</p>
        </div>
        
        <h2>⚙️ Como Configurar:</h2>
        <ol style="color: #5F9EA0;">
            <li>Obtenha sua chave API no Bling (Configurações > API)</li>
            <li>Substitua <code>SEU_TOKEN_API_AQUI</code> no código</li>
            <li>Execute a aplicação e use o front-end Vue.js</li>
        </ol>
        
        <h2>📚 Documentação Bling:</h2>
        <p><a href="https://developer.bling.com.br/aplicativos" style="color: #20B2AA;">https://developer.bling.com.br</a></p>
    </body>
    </html>
    """

@app.route('/status', methods=['GET'])
def status():
    """
    Verifica se a API está funcionando
    """
    return jsonify({
        "status": "online",
        "message": "API funcionando corretamente",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "bling_configured": BLING_API_KEY != "SEU_TOKEN_API_AQUI"
    })

@app.route('/testar-conexao', methods=['GET'])
def testar_conexao():
    """
    Testa a conexão com a API do Bling
    """
    if BLING_API_KEY == "SEU_TOKEN_API_AQUI":
        return jsonify({
            "success": False,
            "error": "Token da API do Bling não configurado"
        }), 400
    
    headers = {
        "Authorization": f"Bearer {BLING_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Tenta listar produtos (apenas para testar)
        response = requests.get(
            "https://www.bling.com.br/Api/v3/produtos",
            headers=headers,
            params={"limite": 1},
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Conexão com Bling estabelecida com sucesso!",
                "status_code": response.status_code
            })
        else:
            return jsonify({
                "success": False,
                "message": "Erro ao conectar com o Bling",
                "status_code": response.status_code,
                "error": response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Erro ao testar conexão: {str(e)}"
        }), 500

@app.route('/cadastrar-produto', methods=['POST'])
def cadastrar_produto_unico():
    """
    Cadastra um único produto no Bling
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "Nenhum dado enviado"}), 400
        
        # Valida campos obrigatórios
        campos_obrigatorios = ['codigo', 'descricao', 'preco']
        campos_faltantes = [campo for campo in campos_obrigatorios if not data.get(campo)]
        
        if campos_faltantes:
            return jsonify({
                "error": f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}"
            }), 400
        
        # Envia para o Bling
        resultado = criar_produto_bling(data)
        
        return jsonify(resultado), resultado.get('status_code', 500)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro no servidor: {str(e)}",
            "success": False
        }), 500

@app.route('/cadastrar-produtos-massa', methods=['POST'])
def cadastrar_produtos_massa():
    """
    Cadastra múltiplos produtos de uma vez
    """
    try:
        data = request.json
        produtos = data.get('produtos', [])
        
        if not produtos:
            return jsonify({"error": "Nenhum produto fornecido"}), 400
        
        if not isinstance(produtos, list):
            return jsonify({"error": "O campo 'produtos' deve ser uma lista"}), 400
        
        print(f"\n{'='*60}")
        print(f"🚀 Iniciando cadastro em massa de {len(produtos)} produtos")
        print(f"{'='*60}\n")
        
        resultados = []
        
        # Processa cada produto
        for idx, produto in enumerate(produtos):
            print(f"[{idx + 1}/{len(produtos)}] Processando: {produto.get('descricao', 'Sem descrição')}")
            
            # Valida campos obrigatórios
            if not all(produto.get(k) for k in ['codigo', 'descricao', 'preco']):
                resultados.append({
                    "produto": produto.get('descricao', 'Sem descrição'),
                    "index": idx,
                    "success": False,
                    "status_code": 400,
                    "error": "Campos obrigatórios faltando (codigo, descricao, preco)"
                })
                continue
            
            # Envia para o Bling
            resultado = criar_produto_bling(produto)
            
            resultados.append({
                "produto": produto.get('descricao', 'Sem descrição'),
                "codigo": produto.get('codigo', 'N/A'),
                "index": idx,
                "success": resultado['success'],
                "status_code": resultado['status_code'],
                "response": resultado.get('response', {}),
                "error": resultado.get('error', None),
                "timestamp": resultado['timestamp']
            })
            
            # Pequena pausa entre requisições para não sobrecarregar a API
            import time
            time.sleep(0.5)
        
        # Calcula estatísticas
        total = len(resultados)
        sucessos = sum(1 for r in resultados if r['success'])
        falhas = total - sucessos
        
        print(f"\n{'='*60}")
        print(f"✅ Resultado: {sucessos} sucesso(s) | ❌ {falhas} falha(s)")
        print(f"{'='*60}\n")
        
        return jsonify({
            "total": total,
            "sucessos": sucessos,
            "falhas": falhas,
            "taxa_sucesso": f"{(sucessos/total)*100:.1f}%" if total > 0 else "0%",
            "detalhes": resultados,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Erro no servidor: {str(e)}",
            "success": False
        }), 500

@app.route('/exemplo-produto', methods=['GET'])
def exemplo_produto():
    """
    Retorna um exemplo de estrutura de produto
    """
    exemplo = {
        "codigo": "PROD001",
        "descricao": "Produto Exemplo",
        "unidade": "Un",
        "situacao": "Ativo",
        "preco": 99.90,
        "precoCusto": 50.00,
        "precoCompra": 45.00,
        "estoque": 100,
        "estoqueMinimo": 10,
        "estoqueMaximo": 500,
        "localizacao": "A1",
        "pesoLiquido": 0.5,
        "pesoBruto": 0.6,
        "largura": 10,
        "altura": 15,
        "profundidade": 20,
        "volumes": 1,
        "itensPorCaixa": 12,
        "unidadeMedida": "Centímetro",
        "ncm": "2106.90.30",
        "origem": "0",
        "cest": "",
        "gtinEan": "7898407015702",
        "gtinEanEmbalagem": "7898407015702",
        "marca": "Marca Exemplo",
        "fornecedor": "Fornecedor XYZ",
        "codigoFornecedor": "FORN001",
        "tipoProducao": "Própria",
        "condicao": "NOVO",
        "freteGratis": "NÃO",
        "categoria": "Eletrônicos>>Smartphones",
        "grupoProdutos": "Linha Premium",
        "descricaoCurta": "Descrição breve do produto",
        "descricaoComplementar": "Descrição detalhada do produto com todas as especificações",
        "observacoes": "Observações internas",
        "imagens": []
    }
    
    return jsonify(exemplo)

@app.route('/upload-imagem', methods=['POST'])
def upload_imagem():
    """
    Endpoint preparado para receber upload de imagens
    No futuro, você pode integrar com sua API de imagens
    """
    try:
        if 'image' not in request.files:
            return jsonify({"error": "Nenhuma imagem enviada"}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({"error": "Nome de arquivo vazio"}), 400
        
        # Aqui você pode:
        # 1. Salvar localmente
        # 2. Enviar para serviço de storage (S3, Cloudinary, etc)
        # 3. Enviar para sua API de imagens
        
        # Por enquanto, retorna sucesso simulado
        return jsonify({
            "success": True,
            "url": f"https://exemplo.com/imagens/{file.filename}",
            "message": "Imagem recebida com sucesso (implementar integração)"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao fazer upload: {str(e)}",
            "success": False
        }), 500

# ==================== TRATAMENTO DE ERROS ====================

@app.errorhandler(404)
def not_found(error):
    """Trata erros 404"""
    return jsonify({
        "error": "Endpoint não encontrado",
        "message": "Verifique a URL e tente novamente"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Trata erros 500"""
    return jsonify({
        "error": "Erro interno do servidor",
        "message": "Ocorreu um erro inesperado"
    }), 500

# ==================== EXECUÇÃO ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 API DE CADASTRO EM MASSA - BLING")
    print("="*60)
    print("✅ Servidor iniciado com sucesso!")
    print("📡 Acesse: http://localhost:5000")
    print("📚 Documentação: http://localhost:5000")
    
    if BLING_API_KEY == "SEU_TOKEN_API_AQUI":
        print("⚠️  ATENÇÃO: Configure seu token do Bling!")
    else:
        print("✅ Token do Bling configurado")
    
    print("="*60 + "\n")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )