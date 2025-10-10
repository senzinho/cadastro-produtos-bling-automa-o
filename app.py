from flask import Flask, request, jsonify, redirect, session, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime
import secrets
import sqlite3
import base64
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

# ==================== CONFIGURAÇÕES ====================
BLING_CLIENT_ID = "9a332428b534dcb305d81f6e0a464be5daa1d1cf"
BLING_CLIENT_SECRET = "af48bb281205050775fa63636972c7f2423632750407ea8fcc4594b00f50"
BLING_REDIRECT_URI = "http://localhost:5000/callback"

BLING_AUTH_URL = "https://www.bling.com.br/Api/v3/oauth/authorize"
BLING_TOKEN_URL = "https://www.bling.com.br/Api/v3/oauth/token"
BLING_API_BASE_URL = "https://www.bling.com.br/Api/v3"

# Configuração de diretórios
UPLOAD_FOLDER = 'uploads/produtos'
DATABASE = 'produtos.db'

# Criar pasta de uploads se não existir
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

TOKENS = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": None
}

# ==================== BANCO DE DADOS ====================

def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            descricao TEXT NOT NULL,
            unidade TEXT,
            situacao TEXT,
            preco REAL,
            preco_custo REAL,
            preco_compra REAL,
            estoque REAL,
            estoque_minimo REAL,
            estoque_maximo REAL,
            localizacao TEXT,
            peso_liquido REAL,
            peso_bruto REAL,
            largura REAL,
            altura REAL,
            profundidade REAL,
            volumes INTEGER,
            itens_por_caixa REAL,
            unidade_medida TEXT,
            ncm TEXT,
            origem TEXT,
            cest TEXT,
            gtin_ean TEXT,
            gtin_ean_embalagem TEXT,
            marca TEXT,
            fornecedor TEXT,
            codigo_fornecedor TEXT,
            tipo_producao TEXT,
            condicao TEXT,
            frete_gratis TEXT,
            categoria TEXT,
            grupo_produtos TEXT,
            descricao_curta TEXT,
            descricao_complementar TEXT,
            observacoes TEXT,
            imagens TEXT,
            enviado_bling BOOLEAN DEFAULT 0,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            codigo_produto TEXT,
            status_code INTEGER,
            sucesso BOOLEAN,
            resposta_bling TEXT,
            erro TEXT,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")

def salvar_imagem(base64_string, codigo_produto, index):
    """Salva imagem base64 e retorna o link"""
    try:
        # Remove o prefixo data:image se existir
        if 'base64,' in base64_string:
            base64_data = base64_string.split('base64,')[1]
        else:
            base64_data = base64_string
        
        # Decodifica a imagem
        image_data = base64.b64decode(base64_data)
        
        # Gera nome único para o arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{codigo_produto}_{timestamp}_{index}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salva o arquivo
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Retorna o link local
        return f"http://localhost:5000/uploads/produtos/{filename}"
    
    except Exception as e:
        print(f"❌ Erro ao salvar imagem: {e}")
        return None

def processar_imagens(imagens, codigo_produto):
    """Processa as imagens: converte base64 em arquivos ou mantém URLs"""
    imagens_processadas = []
    
    if not imagens or not isinstance(imagens, list):
        return imagens_processadas
    
    for idx, img in enumerate(imagens):
        if not img:
            continue
        
        # Se é base64, converte para arquivo
        if img.startswith('data:'):
            url = salvar_imagem(img, codigo_produto, idx)
            if url:
                imagens_processadas.append(url)
        # Se já é URL, mantém
        elif img.startswith('http'):
            imagens_processadas.append(img)
    
    return imagens_processadas

def salvar_produto_db(produto_data):
    """Salva um produto no banco de dados"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Processa as imagens
        imagens_originais = produto_data.get('imagens', [])
        imagens_processadas = processar_imagens(imagens_originais, produto_data.get('codigo', 'sem_codigo'))
        
        cursor.execute('''
            INSERT OR REPLACE INTO produtos (
                codigo, descricao, unidade, situacao, preco, preco_custo, preco_compra,
                estoque, estoque_minimo, estoque_maximo, localizacao,
                peso_liquido, peso_bruto, largura, altura, profundidade,
                volumes, itens_por_caixa, unidade_medida, ncm, origem, cest,
                gtin_ean, gtin_ean_embalagem, marca, fornecedor, codigo_fornecedor,
                tipo_producao, condicao, frete_gratis, categoria, grupo_produtos,
                descricao_curta, descricao_complementar, observacoes, imagens,
                data_atualizacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            produto_data.get('codigo'),
            produto_data.get('descricao'),
            produto_data.get('unidade'),
            produto_data.get('situacao'),
            produto_data.get('preco'),
            produto_data.get('precoCusto'),
            produto_data.get('precoCompra'),
            produto_data.get('estoque'),
            produto_data.get('estoqueMinimo'),
            produto_data.get('estoqueMaximo'),
            produto_data.get('localizacao'),
            produto_data.get('pesoLiquido'),
            produto_data.get('pesoBruto'),
            produto_data.get('largura'),
            produto_data.get('altura'),
            produto_data.get('profundidade'),
            produto_data.get('volumes'),
            produto_data.get('itensPorCaixa'),
            produto_data.get('unidadeMedida'),
            produto_data.get('ncm'),
            produto_data.get('origem'),
            produto_data.get('cest'),
            produto_data.get('gtinEan'),
            produto_data.get('gtinEanEmbalagem'),
            produto_data.get('marca'),
            produto_data.get('fornecedor'),
            produto_data.get('codigoFornecedor'),
            produto_data.get('tipoProducao'),
            produto_data.get('condicao'),
            produto_data.get('freteGratis'),
            produto_data.get('categoria'),
            produto_data.get('grupoProdutos'),
            produto_data.get('descricaoCurta'),
            produto_data.get('descricaoComplementar'),
            produto_data.get('observacoes'),
            json.dumps(imagens_processadas)
        ))
        
        conn.commit()
        produto_id = cursor.lastrowid
        
        return {
            "success": True,
            "produto_id": produto_id,
            "codigo": produto_data.get('codigo'),
            "imagens_processadas": imagens_processadas
        }
    
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        conn.close()

def registrar_envio_bling(produto_id, codigo_produto, resultado):
    """Registra o envio para o Bling no histórico"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO historico_envios (
                produto_id, codigo_produto, status_code, sucesso, 
                resposta_bling, erro, data_envio
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            produto_id,
            codigo_produto,
            resultado.get('status_code'),
            resultado.get('success'),
            json.dumps(resultado.get('response', {})),
            resultado.get('error')
        ))
        
        # Atualiza flag de enviado no produto
        if resultado.get('success'):
            cursor.execute('''
                UPDATE produtos SET enviado_bling = 1 
                WHERE id = ?
            ''', (produto_id,))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao registrar histórico: {e}")
        conn.rollback()
    finally:
        conn.close()

def buscar_produto_db(codigo):
    """Busca um produto no banco pelo código"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM produtos WHERE codigo = ?', (codigo,))
    produto = cursor.fetchone()
    
    conn.close()
    
    if produto:
        return dict(produto)
    return None

def listar_produtos_db(filtro=None):
    """Lista todos os produtos do banco com filtros opcionais"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM produtos'
    params = []
    
    if filtro:
        if filtro.get('enviado_bling') is not None:
            query += ' WHERE enviado_bling = ?'
            params.append(filtro['enviado_bling'])
    
    query += ' ORDER BY data_cadastro DESC'
    
    cursor.execute(query, params)
    produtos = cursor.fetchall()
    
    conn.close()
    
    return [dict(produto) for produto in produtos]

# ==================== FUNÇÕES DE AUTENTICAÇÃO ====================

def obter_access_token(codigo_autorizacao):
    """Troca o código de autorização por um access_token"""
    import base64
    
    credentials = f"{BLING_CLIENT_ID}:{BLING_CLIENT_SECRET}"
    credentials_b64 = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0',
        'Authorization': f'Basic {credentials_b64}'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': codigo_autorizacao,
        'redirect_uri': BLING_REDIRECT_URI
    }
    
    try:
        response = requests.post(BLING_TOKEN_URL, headers=headers, data=data)
        
        print(f"\n{'='*60}")
        print("📤 Requisição enviada para obter token:")
        print(f"URL: {BLING_TOKEN_URL}")
        print(f"Status: {response.status_code}")
        print(f"{'='*60}\n")
        
        response.raise_for_status()
        
        tokens = response.json()
        
        TOKENS['access_token'] = tokens['access_token']
        TOKENS['refresh_token'] = tokens['refresh_token']
        TOKENS['expires_at'] = datetime.now().timestamp() + tokens['expires_in']
        
        print(f"✅ Token obtido com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao obter token: {e}")
        return False

def renovar_access_token():
    """Renova o access_token usando o refresh_token"""
    if not TOKENS['refresh_token']:
        return False
    
    import base64
    
    credentials = f"{BLING_CLIENT_ID}:{BLING_CLIENT_SECRET}"
    credentials_b64 = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0',
        'Authorization': f'Basic {credentials_b64}'
    }
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': TOKENS['refresh_token']
    }
    
    try:
        response = requests.post(BLING_TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        tokens = response.json()
        
        TOKENS['access_token'] = tokens['access_token']
        TOKENS['expires_at'] = datetime.now().timestamp() + tokens['expires_in']
        
        print("✅ Token renovado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao renovar token: {e}")
        return False

def verificar_token():
    """Verifica se o token está válido e renova se necessário"""
    if not TOKENS['access_token']:
        return False
    
    if TOKENS['expires_at'] and datetime.now().timestamp() > (TOKENS['expires_at'] - 300):
        return renovar_access_token()
    
    return True

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/auth/iniciar', methods=['GET'])
def iniciar_autenticacao():
    """Inicia o fluxo OAuth - redireciona para o Bling"""
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    
    params = {
        'response_type': 'code',
        'client_id': BLING_CLIENT_ID,
        'redirect_uri': BLING_REDIRECT_URI,
        'state': state
    }
    
    url = f"{BLING_AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    return redirect(url)

@app.route('/callback', methods=['GET'])
def callback():
    """Recebe o callback do Bling após autorização"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if state != session.get('oauth_state'):
        return jsonify({"error": "State inválido"}), 400
    
    if not code:
        return jsonify({"error": "Código de autorização não recebido"}), 400
    
    if obter_access_token(code):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Autorização Concluída</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 600px; 
                    margin: 100px auto; 
                    text-align: center;
                    background: #0f1419;
                    color: #20B2AA;
                    padding: 20px;
                }
                .success { 
                    background: #161f27; 
                    padding: 30px; 
                    border-radius: 10px;
                    border: 2px solid #20B2AA;
                }
                h1 { color: #20B2AA; }
                button {
                    background: #20B2AA;
                    color: #000;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="success">
                <h1>✅ Autorização Concluída!</h1>
                <p>Sua aplicação foi autorizada com sucesso no Bling.</p>
                <button onclick="window.close()">Fechar</button>
            </div>
        </body>
        </html>
        """
    else:
        return jsonify({"error": "Erro ao obter token"}), 500

@app.route('/auth/status', methods=['GET'])
def status_autenticacao():
    """Verifica o status da autenticação"""
    return jsonify({
        "autenticado": TOKENS['access_token'] is not None,
        "token_valido": verificar_token(),
        "expira_em": int(TOKENS['expires_at'] - datetime.now().timestamp()) if TOKENS['expires_at'] else None
    })

# ==================== FUNÇÕES AUXILIARES BLING ====================

def converter_para_formato_bling(produto):
    """Converte os dados do formulário para o formato esperado pela API do Bling"""
    
    produto_bling = {
        "nome": produto.get('descricao', ''),
        "codigo": produto.get('codigo', ''),
        "preco": float(produto.get('preco', 0)),
        "tipo": "P",
        "situacao": "A" if produto.get('situacao') == "Ativo" else "I",
        "formato": "S",
        "descricaoCurta": produto.get('descricaoCurta', ''),
        "descricaoComplementar": produto.get('descricaoComplementar', ''),
        "unidade": produto.get('unidade', 'UN'),
        "marca": produto.get('marca', ''),
    }
    
    if produto.get('pesoLiquido'):
        produto_bling['pesoLiquido'] = float(produto.get('pesoLiquido'))
    
    if produto.get('pesoBruto'):
        produto_bling['pesoBruto'] = float(produto.get('pesoBruto'))
    
    if produto.get('volumes'):
        produto_bling['volumes'] = int(produto.get('volumes', 1))
    
    if produto.get('itensPorCaixa'):
        produto_bling['itensPorCaixa'] = float(produto.get('itensPorCaixa', 0))
    
    if produto.get('gtinEan'):
        produto_bling['gtin'] = produto.get('gtinEan')
    
    if produto.get('gtinEanEmbalagem'):
        produto_bling['gtinEmbalagem'] = produto.get('gtinEanEmbalagem')
    
    if produto.get('ncm'):
        produto_bling['ncm'] = produto.get('ncm')
    
    if produto.get('origem'):
        produto_bling['origem'] = int(produto.get('origem', 0))
    
    if produto.get('cest'):
        produto_bling['cest'] = produto.get('cest')
    
    tipo_producao_map = {'Própria': 'P', 'Terceiros': 'T'}
    if produto.get('tipoProducao'):
        produto_bling['tipoProducao'] = tipo_producao_map.get(produto.get('tipoProducao'), 'P')
    
    condicao_map = {'NOVO': 0, 'USADO': 2}
    if produto.get('condicao'):
        produto_bling['condicao'] = condicao_map.get(produto.get('condicao'), 0)
    
    if produto.get('freteGratis'):
        produto_bling['freteGratis'] = produto.get('freteGratis') == 'SIM'
    
    estoque_data = {}
    if produto.get('estoqueMinimo'):
        estoque_data['minimo'] = float(produto.get('estoqueMinimo', 0))
    if produto.get('estoqueMaximo'):
        estoque_data['maximo'] = float(produto.get('estoqueMaximo', 0))
    if produto.get('localizacao'):
        estoque_data['localizacao'] = produto.get('localizacao')
    
    if estoque_data:
        produto_bling['estoque'] = estoque_data
    
    dimensoes_data = {}
    if produto.get('largura'):
        dimensoes_data['largura'] = float(produto.get('largura'))
    if produto.get('altura'):
        dimensoes_data['altura'] = float(produto.get('altura'))
    if produto.get('profundidade'):
        dimensoes_data['profundidade'] = float(produto.get('profundidade'))
    
    unidade_medida_map = {'Centímetro': 1, 'Metro': 2}
    if produto.get('unidadeMedida'):
        dimensoes_data['unidadeMedida'] = unidade_medida_map.get(produto.get('unidadeMedida'), 1)
    
    if dimensoes_data:
        produto_bling['dimensoes'] = dimensoes_data
    
    # Busca as imagens processadas do banco se o produto já existe
    produto_db = buscar_produto_db(produto.get('codigo'))
    if produto_db and produto_db.get('imagens'):
        imagens_urls = json.loads(produto_db['imagens'])
        if imagens_urls:
            produto_bling['imagens'] = [
                {"tipo": "E", "url": url} for url in imagens_urls[:8]
            ]
    
    if produto.get('observacoes'):
        produto_bling['observacoes'] = produto.get('observacoes')
    
    return produto_bling

def criar_produto_bling(produto_data):
    """Envia um produto para a API do Bling"""
    
    if not verificar_token():
        return {
            "status_code": 401,
            "error": "Não autenticado. Acesse /auth/iniciar para autorizar",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
    
    produto_bling = converter_para_formato_bling(produto_data)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKENS['access_token']}"
    }
    
    try:
        response = requests.post(
            f"{BLING_API_BASE_URL}/produtos",
            headers=headers,
            json=produto_bling,
            timeout=30
        )
        
        print(f"[{datetime.now()}] Produto: {produto_bling.get('nome', 'N/A')} - Status: {response.status_code}")
        
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

# ==================== ROTAS ====================

@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação"""
    autenticado = TOKENS['access_token'] is not None
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM produtos')
    total_produtos = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM produtos WHERE enviado_bling = 1')
    produtos_enviados = cursor.fetchone()[0]
    conn.close()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Cadastro Bling com SQLite</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                max-width: 900px; 
                margin: 50px auto; 
                padding: 20px;
                background: #0f1419;
                color: #20B2AA;
            }}
            h1 {{ color: #20B2AA; }}
            h2 {{ color: #5F9EA0; margin-top: 30px; }}
            .stats {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: #161f27;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #20B2AA;
                text-align: center;
            }}
            .stat-number {{
                font-size: 48px;
                font-weight: bold;
                color: #20B2AA;
            }}
            .endpoint {{ 
                background: #161f27; 
                padding: 15px; 
                margin: 10px 0; 
                border-left: 4px solid #20B2AA;
                border-radius: 5px;
            }}
            code {{ 
                background: #0f1419; 
                padding: 2px 6px; 
                border-radius: 3px;
                color: #20B2AA;
            }}
            .method {{ 
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: bold;
                margin-right: 10px;
            }}
            .post {{ background: #20B2AA; color: #000; }}
            .get {{ background: transparent; border: 2px solid #20B2AA; color: #20B2AA; }}
            .status {{ 
                padding: 20px; 
                background: #161f27; 
                border-radius: 10px;
                margin: 20px 0;
                border: 2px solid {'#20B2AA' if autenticado else '#FF4444'};
            }}
            .btn {{
                background: #20B2AA;
                color: #000;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>🚀 API de Cadastro em Massa - Bling + SQLite</h1>
        <p>Sistema para cadastrar produtos no Bling via API v3 com banco de dados local</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_produtos}</div>
                <div>Produtos Cadastrados</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{produtos_enviados}</div>
                <div>Enviados ao Bling</div>
            </div>
        </div>
        
        <div class="status">
            <h3>Status da Autenticação</h3>
            <p>{'✅ Autenticado e pronto para usar!' if autenticado else '⚠️ Não autenticado'}</p>
            {'' if autenticado else '<a href="/auth/iniciar" class="btn">🔐 Autorizar Aplicação</a>'}
        </div>
        
        <h2>📦 Endpoints de Produtos (com BD):</h2>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/cadastrar-produto</strong>
            <p>Cadastra produto no banco E envia para o Bling</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/salvar-produto</strong>
            <p>Salva produto APENAS no banco (sem enviar ao Bling)</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/produtos</strong>
            <p>Lista todos os produtos do banco</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/produtos/&lt;codigo&gt;</strong>
            <p>Busca um produto específico pelo código</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/enviar-produto-bling/&lt;codigo&gt;</strong>
            <p>Envia um produto já salvo para o Bling</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/uploads/produtos/&lt;filename&gt;</strong>
            <p>Acessa uma imagem de produto salva</p>
        </div>
        
        <h2>📝 Exemplo de uso:</h2>
        <code style="display: block; padding: 15px; white-space: pre;">
POST /salvar-produto
{
    "codigo": "PROD001",
    "descricao": "Produto Teste",
    "preco": 99.90,
    "imagens": ["data:image/jpeg;base64,..."]  // Será convertida em link
}
        </code>
    </body>
    </html>
    """

@app.route('/status', methods=['GET'])
def status():
    """Verifica se a API está funcionando"""
    return jsonify({
        "status": "online",
        "message": "API funcionando corretamente",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "autenticado": TOKENS['access_token'] is not None,
        "database": os.path.exists(DATABASE)
    })

# Rota para servir imagens
@app.route('/uploads/produtos/<filename>')
def servir_imagem(filename):
    """Serve as imagens salvas"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/salvar-produto', methods=['POST'])
def salvar_produto_endpoint():
    """Salva um produto APENAS no banco de dados (não envia ao Bling)"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "Nenhum dado enviado"}), 400
        
        campos_obrigatorios = ['codigo', 'descricao', 'preco']
        campos_faltantes = [campo for campo in campos_obrigatorios if not data.get(campo)]
        
        if campos_faltantes:
            return jsonify({
                "error": f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}"
            }), 400
        
        resultado = salvar_produto_db(data)
        
        if resultado['success']:
            return jsonify({
                "success": True,
                "message": "Produto salvo com sucesso no banco de dados",
                "produto_id": resultado['produto_id'],
                "codigo": resultado['codigo'],
                "imagens": resultado['imagens_processadas'],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": resultado['error']
            }), 500
        
    except Exception as e:
        return jsonify({
            "error": f"Erro no servidor: {str(e)}",
            "success": False
        }), 500

@app.route('/cadastrar-produto', methods=['POST'])
def cadastrar_produto_unico():
    """Salva no banco E envia para o Bling"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "Nenhum dado enviado"}), 400
        
        campos_obrigatorios = ['codigo', 'descricao', 'preco']
        campos_faltantes = [campo for campo in campos_obrigatorios if not data.get(campo)]
        
        if campos_faltantes:
            return jsonify({
                "error": f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}"
            }), 400
        
        # 1. Salva no banco
        resultado_db = salvar_produto_db(data)
        
        if not resultado_db['success']:
            return jsonify({
                "success": False,
                "error": f"Erro ao salvar no banco: {resultado_db['error']}"
            }), 500
        
        # 2. Envia para o Bling
        resultado_bling = criar_produto_bling(data)
        
        # 3. Registra o envio
        registrar_envio_bling(
            resultado_db['produto_id'],
            data.get('codigo'),
            resultado_bling
        )
        
        return jsonify({
            "success": resultado_bling['success'],
            "produto_id": resultado_db['produto_id'],
            "imagens": resultado_db['imagens_processadas'],
            "bling": resultado_bling,
            "timestamp": datetime.now().isoformat()
        }), resultado_bling.get('status_code', 500)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro no servidor: {str(e)}",
            "success": False
        }), 500

@app.route('/produtos', methods=['GET'])
def listar_produtos():
    """Lista todos os produtos do banco"""
    try:
        enviado = request.args.get('enviado_bling')
        
        filtro = {}
        if enviado is not None:
            filtro['enviado_bling'] = int(enviado)
        
        produtos = listar_produtos_db(filtro)
        
        # Converte imagens de JSON string para lista
        for produto in produtos:
            if produto.get('imagens'):
                produto['imagens'] = json.loads(produto['imagens'])
        
        return jsonify({
            "total": len(produtos),
            "produtos": produtos
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao listar produtos: {str(e)}"
        }), 500

@app.route('/produtos/<codigo>', methods=['GET'])
def buscar_produto(codigo):
    """Busca um produto específico"""
    try:
        produto = buscar_produto_db(codigo)
        
        if not produto:
            return jsonify({"error": "Produto não encontrado"}), 404
        
        # Converte imagens de JSON string para lista
        if produto.get('imagens'):
            produto['imagens'] = json.loads(produto['imagens'])
        
        return jsonify(produto)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao buscar produto: {str(e)}"
        }), 500

@app.route('/enviar-produto-bling/<codigo>', methods=['POST'])
def enviar_produto_bling_endpoint(codigo):
    """Envia um produto já salvo no banco para o Bling"""
    try:
        produto = buscar_produto_db(codigo)
        
        if not produto:
            return jsonify({"error": "Produto não encontrado no banco"}), 404
        
        # Converte de volta para o formato do formulário
        produto_data = {
            'codigo': produto['codigo'],
            'descricao': produto['descricao'],
            'preco': produto['preco'],
            'unidade': produto['unidade'],
            'situacao': produto['situacao'],
            # ... adicione outros campos conforme necessário
        }
        
        resultado = criar_produto_bling(produto_data)
        
        registrar_envio_bling(produto['id'], codigo, resultado)
        
        return jsonify(resultado), resultado.get('status_code', 500)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao enviar produto: {str(e)}",
            "success": False
        }), 500

@app.route('/cadastrar-produtos-massa', methods=['POST'])
def cadastrar_produtos_massa():
    """Cadastra múltiplos produtos: salva no BD e envia ao Bling"""
    try:
        data = request.json
        produtos = data.get('produtos', [])
        
        if not produtos:
            return jsonify({"error": "Nenhum produto fornecido"}), 400
        
        print(f"\n{'='*60}")
        print(f"🚀 Iniciando cadastro em massa de {len(produtos)} produtos")
        print(f"{'='*60}\n")
        
        resultados = []
        
        for idx, produto in enumerate(produtos):
            print(f"[{idx + 1}/{len(produtos)}] Processando: {produto.get('descricao', 'Sem descrição')}")
            
            # Salva no banco
            resultado_db = salvar_produto_db(produto)
            
            if not resultado_db['success']:
                resultados.append({
                    "produto": produto.get('descricao'),
                    "index": idx,
                    "success": False,
                    "error": "Erro ao salvar no banco"
                })
                continue
            
            # Envia para o Bling
            resultado_bling = criar_produto_bling(produto)
            
            # Registra histórico
            registrar_envio_bling(
                resultado_db['produto_id'],
                produto.get('codigo'),
                resultado_bling
            )
            
            resultados.append({
                "produto": produto.get('descricao'),
                "codigo": produto.get('codigo'),
                "index": idx,
                "produto_id": resultado_db['produto_id'],
                "imagens": resultado_db['imagens_processadas'],
                "success": resultado_bling['success'],
                "status_code": resultado_bling['status_code'],
                "error": resultado_bling.get('error')
            })
            
            import time
            time.sleep(0.5)
        
        total = len(resultados)
        sucessos = sum(1 for r in resultados if r['success'])
        falhas = total - sucessos
        
        return jsonify({
            "total": total,
            "sucessos": sucessos,
            "falhas": falhas,
            "taxa_sucesso": f"{(sucessos/total)*100:.1f}%",
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
    """Retorna um exemplo de estrutura de produto"""
    exemplo = {
        "codigo": "PROD001",
        "descricao": "Produto Exemplo",
        "unidade": "Un",
        "situacao": "Ativo",
        "preco": 99.90,
        "imagens": [
            "http://localhost:5000/uploads/produtos/imagem1.jpg",
            "data:image/jpeg;base64,/9j/4AAQ..."  # Será convertida automaticamente
        ]
    }
    
    return jsonify(exemplo)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint não encontrado"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Erro interno do servidor"
    }), 500

if __name__ == '__main__':
    init_db()
    
    print("\n" + "="*60)
    print("🚀 API DE CADASTRO EM MASSA - BLING V3 + SQLite")
    print("="*60)
    print("✅ Servidor iniciado com sucesso!")
    print("📡 Acesse: http://localhost:5000")
    print("🗄️  Banco de dados: produtos.db")
    print("📁 Imagens em: uploads/produtos/")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)