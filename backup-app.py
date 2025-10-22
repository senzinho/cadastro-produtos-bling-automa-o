from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import json
from functools import wraps
import traceback

app = Flask(__name__)

# Configurações de segurança do Jinja2
app.jinja_env.block_start_string = '{%'
app.jinja_env.block_end_string = '%}'
app.jinja_env.variable_start_string = '{{'
app.jinja_env.variable_end_string = '}}'
app.jinja_env.comment_start_string = '{#'
app.jinja_env.comment_end_string = '#}'

class RawTemplateString(str):
    def __html__(self):
        return self

@app.template_filter('raw')
def raw_filter(s):
    return RawTemplateString(s)

# Configuração do CORS
CORS(app, supports_credentials=True, origins=['http://localhost:*', 'http://127.0.0.1:*'])

# Configurações
app.config['SECRET_KEY'] = 'sua-chave-secreta-super-segura-aqui-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://policia:Saopio22.20305@localhost/controle_acessos'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

db = SQLAlchemy(app)

# ==================== MODELOS DO BANCO DE DADOS ====================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    calculations = db.relationship('Calculation', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Marketplace(db.Model):
    __tablename__ = 'marketplaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    commission = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id - 1,
            'name': self.name,
            'commission': self.commission,
            'active': self.active
        }

class KitConfig(db.Model):
    __tablename__ = 'kit_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    kits_data = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id - 1,
            'name': self.name,
            'kits': json.loads(self.kits_data),
            'active': self.active
        }

class Calculation(db.Model):
    __tablename__ = 'calculations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    calculation_type = db.Column(db.String(50), nullable=False)
    marketplace_id = db.Column(db.Integer, db.ForeignKey('marketplaces.id'))
    cost = db.Column(db.Float)
    price = db.Column(db.Float)
    margin = db.Column(db.Float)
    tax_rate = db.Column(db.Float)
    result_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'calculation_type': self.calculation_type,
            'marketplace_id': self.marketplace_id,
            'cost': self.cost,
            'price': self.price,
            'margin': self.margin,
            'tax_rate': self.tax_rate,
            'result_data': json.loads(self.result_data) if self.result_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LoginHistory(db.Model):
    __tablename__ = 'login_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    email_attempt = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_attempt': self.email_attempt,
            'ip_address': self.ip_address,
            'success': self.success,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ==================== DECORADORES DE AUTENTICAÇÃO ====================

def login_required(f):
    """Requer que o usuário esteja autenticado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Para rotas HTML, redireciona para login
            if request.endpoint and not request.endpoint.startswith('api'):
                return redirect(url_for('login_page'))
            # Para rotas API, retorna erro JSON
            return jsonify({"error": "Não autenticado"}), 401
        
        # Verifica se o usuário ainda existe e está ativo
        user = User.query.get(session['user_id'])
        if not user or not user.active:
            session.clear()
            if request.endpoint and not request.endpoint.startswith('api'):
                return redirect(url_for('login_page'))
            return jsonify({"error": "Usuário inativo ou não encontrado"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Requer que o usuário seja administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.endpoint and not request.endpoint.startswith('api'):
                return redirect(url_for('login_page'))
            return jsonify({"error": "Não autenticado"}), 401
        
        user = User.query.get(session['user_id'])
        if not user or not user.active:
            session.clear()
            if request.endpoint and not request.endpoint.startswith('api'):
                return redirect(url_for('login_page'))
            return jsonify({"error": "Usuário inativo"}), 401
        
        if user.role != 'admin':
            if request.endpoint and not request.endpoint.startswith('api'):
                return redirect(url_for('calculadora'))
            return jsonify({"error": "Acesso negado. Apenas administradores."}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# ==================== FUNÇÕES AUXILIARES ====================

def init_database():
    """Inicializa o banco de dados com dados padrão"""
    with app.app_context():
        db.create_all()
        print('✅ Tabelas criadas!')
        
        if User.query.count() == 0:
            admin = User(
                name='Admin Sistema',
                email='admin@sistema.com',
                password=generate_password_hash('admin123'),
                role='admin',
                active=True
            )
            
            user = User(
                name='João Silva',
                email='user@sistema.com',
                password=generate_password_hash('user123'),
                role='user',
                active=True
            )
            
            db.session.add(admin)
            db.session.add(user)
            db.session.commit()
            print('✅ Usuários padrão criados!')
        
        if Marketplace.query.count() == 0:
            marketplaces = [
                Marketplace(name="Mercado Livre Premium", commission=0.17),  # ID 1 (index 0) - 17%
                Marketplace(name="Mercado Livre Clássico", commission=0.12), # ID 2 (index 1) - 12%
                Marketplace(name="Americanas", commission=0.16),              # ID 3 (index 2)
                Marketplace(name="Magalu", commission=0.18),                  # ID 4 (index 3)
                Marketplace(name="Via Varejo", commission=0.17),              # ID 5 (index 4)
                Marketplace(name="Droga Raia", commission=0.22),              # ID 6 (index 5)
                Marketplace(name="Tray", commission=0.05),                    # ID 7 (index 6)
                Marketplace(name="Tray + 20%", commission=0.05),              # ID 8 (index 7)
                Marketplace(name="Digigrow", commission=0.18),                # ID 9 (index 8)
                Marketplace(name="Shopee", commission=0.20),                  # ID 10 (index 9)
                Marketplace(name="Shopee x2", commission=0.20)                # ID 11 (index 10)
            ]
            
            for mp in marketplaces:
                db.session.add(mp)
            
            db.session.commit()
            print('✅ Marketplaces criados!')
            print('   • Mercado Livre Premium: ID 1 (index 0) - 17% - Frete 7/27')
            print('   • Mercado Livre Clássico: ID 2 (index 1) - 12% - Frete 7/27')
            print('   • Americanas: ID 3 (index 2) - Frete 7/27')
            print('   • Magalu: ID 4 (index 3) - Frete 7/27')
            print('   • Via Varejo: ID 5 (index 4) - Frete 7/27')
        
        if KitConfig.query.count() == 0:
            kit_configs = [
                KitConfig(
                    name="Kits de 2, 3 e 6",
                    kits_data=json.dumps([
                        {"name": "Kit 2", "multiplier": 2},
                        {"name": "Kit 3", "multiplier": 3},
                        {"name": "Kit 6", "multiplier": 6}
                    ])
                ),
                KitConfig(
                    name="Kits de 4, 12 e 24",
                    kits_data=json.dumps([
                        {"name": "Kit 4", "multiplier": 4},
                        {"name": "Kit 12", "multiplier": 12},
                        {"name": "Kit 24", "multiplier": 24}
                    ])
                ),
                KitConfig(
                    name="Kits de 5, 10 e 20",
                    kits_data=json.dumps([
                        {"name": "Kit 5", "multiplier": 5},
                        {"name": "Kit 10", "multiplier": 10},
                        {"name": "Kit 20", "multiplier": 20}
                    ])
                ),
                KitConfig(
                    name="Kits de 8, 16 e 18",
                    kits_data=json.dumps([
                        {"name": "Kit 8", "multiplier": 8},
                        {"name": "Kit 16", "multiplier": 16},
                        {"name": "Kit 18", "multiplier": 18}
                    ])
                )
            ]
            
            for kc in kit_configs:
                db.session.add(kc)
            
            db.session.commit()
            print('✅ Configurações de kits criadas!')

def get_shipment_value(marketplace_db_id, price=0):
    """
    Calcula o valor do frete baseado no marketplace e preço
    
    ATUALIZADO:
    - IDs 1-5 (Mercado Livre Premium, Mercado Livre Clássico, Americanas, Magalu, Via Varejo): 
      Frete 7.00 ou 27.00 (baseado no preço >= 78)
    - IDs 6-9 (Droga Raia, Tray, Tray + 20%, Digigrow): Frete fixo 1.00
    - IDs 10-11 (Shopee, Shopee x2): Frete fixo 4.50
    """
    marketplace_id = marketplace_db_id - 1
    
    # Droga Raia, Tray, Tray + 20%, Digigrow (IDs 6-9, indices 5-8)
    if marketplace_id >= 5 and marketplace_id <= 8:
        return 1.0
    # Shopee, Shopee x2 (IDs 10-11, indices 9-10)
    elif marketplace_id in [9, 10]:
        return 4.5
    # Mercado Livre Premium, Mercado Livre Clássico, Americanas, Magalu, Via Varejo (IDs 1-5, indices 0-4)
    else:
        if price >= 78:
            return 27.0  # ATUALIZADO: era 22.0
        return 7.0       # ATUALIZADO: era 6.0

def calculate_price(cost, margin, marketplace_db_id, tax_rate, kit_amt=1):
    """Calcula o preço de venda baseado no custo"""
    marketplace = Marketplace.query.get(marketplace_db_id)
    if not marketplace:
        return None, None
    
    commission = marketplace.commission
    marketplace_id = marketplace_db_id - 1
    
    shipment = get_shipment_value(marketplace_db_id, 0)
    price = ((cost * (margin * 0.01 + 1) * kit_amt) + shipment) / (1 - (commission + tax_rate))
    
    # Recalcula se preço >= 78 para os primeiros marketplaces (índices 0-4)
    if marketplace_id <= 4 and price >= 78:
        shipment = 27.0  # ATUALIZADO: era 22.0
        price = ((cost * (margin * 0.01 + 1) * kit_amt) + shipment) / (1 - (commission + tax_rate))
    
    # Shopee x2 (ID 11, índice 10)
    if marketplace_id == 10:
        price *= 2
    # Tray + 20% (ID 8, índice 7)
    elif marketplace_id == 7:
        price = ((price / (1 - 0.10)) / (1 - 0.10))
    
    return price, shipment

def calculate_cost_value(price, margin, marketplace_db_id, tax_rate):
    """Calcula o custo baseado no preço de venda"""
    marketplace = Marketplace.query.get(marketplace_db_id)
    if not marketplace:
        return None, None
    
    commission = marketplace.commission
    marketplace_id = marketplace_db_id - 1
    
    shipment = get_shipment_value(marketplace_db_id, 0)
    cost = (price - (price * (commission + tax_rate)) - shipment) / (1 + margin * 0.01)
    
    # Recalcula se preço >= 78 para os primeiros marketplaces (índices 0-4)
    if marketplace_id <= 4 and price >= 78:
        shipment = 27.0  # ATUALIZADO: era 22.0
        cost = (price - (price * (commission + tax_rate)) - shipment) / (1 + margin * 0.01)
    
    return cost, shipment

# ==================== ROTAS HTML ====================

@app.route('/')
def home():
    """Página inicial - redireciona conforme o papel do usuário"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.active:
            if user.role == 'admin':
                return redirect(url_for('painel'))
            else:
                return redirect(url_for('calculadora'))
    return redirect(url_for('login_page'))

@app.route('/login')
@app.route('/login.html')
def login_page():
    """Página de login"""
    # Se já estiver logado, redireciona
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.active:
            if user.role == 'admin':
                return redirect(url_for('painel'))
            else:
                return redirect(url_for('calculadora'))
    return render_template('login.html')

@app.route('/painel')
@app.route('/painel.html')
@admin_required
def painel():
    """Serve o painel de controle - apenas para admins"""
    return render_template('painel.html')

@app.route('/index')
@app.route('/index.html')
@app.route('/calculadora')
@login_required
def calculadora():
    """Serve a calculadora de preços - apenas para usuários autenticados e ativos"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Página de teste do servidor"""
    return '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>✅ Teste Flask - Sistema Online</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 60px 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 600px;
                width: 100%;
            }
            h1 {
                color: #41644A;
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            .status {
                color: #48bb78;
                font-size: 1.5rem;
                margin: 20px 0;
                font-weight: 600;
            }
            .emoji {
                font-size: 4rem;
                margin: 20px 0;
                animation: bounce 2s infinite;
            }
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-20px); }
            }
            .links {
                list-style: none;
                padding: 0;
                margin: 30px 0;
            }
            .links li {
                margin: 15px 0;
            }
            .links a {
                display: inline-block;
                color: white;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                text-decoration: none;
                font-weight: 600;
                font-size: 1.1rem;
                padding: 15px 30px;
                border-radius: 10px;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
            .links a:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            }
            .info {
                background: #f7fafc;
                padding: 20px;
                border-radius: 10px;
                margin-top: 30px;
                text-align: left;
            }
            .info h3 {
                color: #2d3748;
                margin-bottom: 15px;
            }
            .info p {
                color: #4a5568;
                margin: 8px 0;
                font-size: 0.95rem;
            }
            .info code {
                background: #e2e8f0;
                padding: 2px 8px;
                border-radius: 4px;
                color: #c53030;
                font-family: 'Courier New', monospace;
            }
            .update {
                background: #c6f6d5;
                border: 2px solid #48bb78;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .update h4 {
                color: #22543d;
                margin-bottom: 8px;
            }
            .update ul {
                text-align: left;
                color: #22543d;
                margin-left: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🚀</div>
            <h1>Sistema Online!</h1>
            <div class="status">✅ Flask Funcionando Perfeitamente</div>
            
            <div class="update">
                <h4>🆕 Atualizações Recentes:</h4>
                <ul>
                    <li>✅ Frete alterado: 7/27 (antes era 6/22)</li>
                    <li>✅ Novo: Mercado Livre Clássico (12%)</li>
                    <li>✅ Afeta: ML Premium, ML Clássico, Americanas, Magalu, Via Varejo</li>
                </ul>
            </div>
            
            <ul class="links">
                <li><a href="/login">🔐 Login</a></li>
                <li><a href="/painel">📊 Painel de Controle</a></li>
                <li><a href="/calculadora">🧮 Calculadora de Preços</a></li>
                <li><a href="/api/marketplaces">🔌 API Marketplaces</a></li>
            </ul>

            <div class="info">
                <h3>📋 Informações do Sistema</h3>
                <p>🌐 <strong>URL:</strong> <code>http://localhost:5000</code></p>
                <p>📊 <strong>Banco:</strong> <code>controle_acessos</code></p>
                <p>👤 <strong>Admin:</strong> <code>admin@sistema.com</code> / <code>admin123</code></p>
                <p>👤 <strong>User:</strong> <code>user@sistema.com</code> / <code>user123</code></p>
                <p>🔒 <strong>Segurança:</strong> Autenticação obrigatória para acessar calculadora e painel</p>
            </div>
        </div>
    </body>
    </html>
    '''

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email e senha são obrigatórios"}), 400
        
        user = User.query.filter_by(email=email).first()
        
        login_attempt = LoginHistory(
            user_id=user.id if user else None,
            email_attempt=email,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:255],
            success=False
        )
        
        if not user or not check_password_hash(user.password, password):
            db.session.add(login_attempt)
            db.session.commit()
            return jsonify({"error": "Email ou senha incorretos"}), 401
        
        if not user.active:
            db.session.add(login_attempt)
            db.session.commit()
            return jsonify({"error": "Usuário inativo. Entre em contato com o administrador."}), 401
        
        session.clear()
        session['user_id'] = user.id
        session.permanent = True
        
        user.last_login = datetime.now(timezone.utc)
        login_attempt.success = True
        
        db.session.add(login_attempt)
        db.session.commit()
        
        print(f'✅ Login bem-sucedido: {user.email} (ID: {user.id}, Role: {user.role})')
        
        return jsonify({
            "message": "Login realizado com sucesso",
            "user": user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f'❌ Erro no login: {str(e)}')
        print(f'❌ Traceback completo:')
        traceback.print_exc()
        return jsonify({"error": f"Erro interno no servidor: {str(e)}"}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout - não requer autenticação para permitir limpeza de sessão"""
    user_id = session.get('user_id')
    session.clear()
    
    if user_id:
        user = User.query.get(user_id)
        if user:
            print(f'✅ Logout: {user.email} (ID: {user.id})')
    
    return jsonify({"message": "Logout realizado com sucesso"})

@app.route('/api/me', methods=['GET'])
@login_required
def get_current_user():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404
    return jsonify(user.to_dict())

# ==================== ROTAS DE USUÁRIOS ====================

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    try:
        data = request.json
        
        if not data.get('name') or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Nome, email e senha são obrigatórios"}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "Email já cadastrado"}), 400
        
        user = User(
            name=data['name'],
            email=data['email'],
            password=generate_password_hash(data['password']),
            role=data.get('role', 'user'),
            active=data.get('active', True)
        )
        
        db.session.add(user)
        db.session.commit()
        
        print(f'✅ Usuário criado: {user.email} (ID: {user.id}, Role: {user.role})')
        
        return jsonify({
            "message": "Usuário criado com sucesso",
            "user": user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f'❌ Erro ao criar usuário: {str(e)}')
        return jsonify({"error": "Erro ao criar usuário"}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        data = request.json
        
        if data.get('email') and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({"error": "Email já cadastrado"}), 400
        
        if data.get('name'):
            user.name = data['name']
        if data.get('email'):
            user.email = data['email']
        if data.get('password'):
            user.password = generate_password_hash(data['password'])
        if 'role' in data:
            user.role = data['role']
        if 'active' in data:
            user.active = data['active']
            # Se desativar o usuário, limpa sua sessão
            if not user.active and 'user_id' in session and session['user_id'] == user_id:
                session.clear()
        
        db.session.commit()
        
        print(f'✅ Usuário atualizado: {user.email} (ID: {user.id}, Active: {user.active})')
        
        return jsonify({
            "message": "Usuário atualizado com sucesso",
            "user": user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f'❌ Erro ao atualizar usuário: {str(e)}')
        return jsonify({"error": "Erro ao atualizar usuário"}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        if user.id == session['user_id']:
            return jsonify({"error": "Você não pode deletar sua própria conta"}), 400
        
        email = user.email
        db.session.delete(user)
        db.session.commit()
        
        print(f'✅ Usuário deletado: {email} (ID: {user_id})')
        
        return jsonify({"message": "Usuário deletado com sucesso"})
    
    except Exception as e:
        db.session.rollback()
        print(f'❌ Erro ao deletar usuário: {str(e)}')
        return jsonify({"error": "Erro ao deletar usuário"}), 500

# ==================== ROTAS DE MARKETPLACES ====================

@app.route('/api/marketplaces', methods=['GET'])
def get_marketplaces():
    """Lista marketplaces - pública para facilitar uso"""
    marketplaces = Marketplace.query.filter_by(active=True).all()
    return jsonify([mp.to_dict() for mp in marketplaces])

# ==================== ROTAS DE KITS ====================

@app.route('/api/kits', methods=['GET'])
def get_kits():
    """Lista configurações de kits - pública para facilitar uso"""
    kit_configs = KitConfig.query.filter_by(active=True).all()
    return jsonify([kc.to_dict() for kc in kit_configs])

# ==================== ROTAS DE CÁLCULOS ====================

@app.route('/api/calculate-all-prices', methods=['POST'])
@login_required
def calculate_all_prices():
    try:
        data = request.json
        cost = float(data.get('cost', 0))
        margin = float(data.get('margin', 20))
        tax_rate = float(data.get('tax_rate', 0.1))
        kit_config_id = int(data.get('kit_config_id', 0))
        
        if cost <= 0:
            return jsonify({"error": "Custo deve ser maior que zero"}), 400
        
        kit_config = KitConfig.query.get(kit_config_id + 1)
        if not kit_config:
            return jsonify({"error": "Configuração de kit não encontrada"}), 404
        
        kits_data = json.loads(kit_config.kits_data)
        marketplaces = Marketplace.query.filter_by(active=True).all()
        all_results = []
        
        for marketplace in marketplaces:
            commission = marketplace.commission
            
            single_price, shipment = calculate_price(cost, margin, marketplace.id, tax_rate, 1)
            
            if single_price is None:
                continue
            
            only_commission = single_price * commission
            only_tax = single_price * tax_rate
            profit = cost * (margin * 0.01)
            
            kits_prices = []
            for kit in kits_data:
                kit_price, _ = calculate_price(cost, margin, marketplace.id, tax_rate, kit["multiplier"])
                kits_prices.append({
                    "name": kit["name"],
                    "multiplier": kit["multiplier"],
                    "price": round(kit_price, 2)
                })
            
            # Determina a mensagem do frete baseado no marketplace_id
            marketplace_id = marketplace.id - 1
            if marketplace_id <= 4:  # ML Premium, ML Clássico, Americanas, Magalu, Via Varejo
                shipment_display = "7.00 ou 27.00"
            else:
                shipment_display = str(shipment)
            
            all_results.append({
                "marketplace_id": marketplace.id - 1,
                "marketplace_name": marketplace.name,
                "single_price": round(single_price, 2),
                "kits": kits_prices,
                "shipment": shipment_display,
                "commission": round(only_commission, 2),
                "tax": round(only_tax, 2),
                "profit": round(profit, 2)
            })
        
        calculation = Calculation(
            user_id=session['user_id'],
            calculation_type='price',
            cost=cost,
            margin=margin,
            tax_rate=tax_rate,
            result_data=json.dumps(all_results)
        )
        db.session.add(calculation)
        db.session.commit()
        
        return jsonify({
            "results": all_results,
            "kit_config_name": kit_config.name
        })
    
    except Exception as e:
        print(f'❌ Erro ao calcular preços: {str(e)}')
        traceback.print_exc()
        return jsonify({"error": "Erro ao calcular preços"}), 500

@app.route('/api/calculate-cost', methods=['POST'])
@login_required
def calculate_cost_endpoint():
    try:
        data = request.json
        price = float(data.get('price', 0))
        margin = float(data.get('margin', 20))
        tax_rate = float(data.get('tax_rate', 0.1))
        marketplace_id = int(data.get('marketplace_id', 0))
        
        if price <= 0:
            return jsonify({"error": "Preço deve ser maior que zero"}), 400
        
        marketplace = Marketplace.query.get(marketplace_id + 1)
        if not marketplace:
            return jsonify({"error": "Marketplace não encontrado"}), 404
        
        cost, shipment = calculate_cost_value(price, margin, marketplace.id, tax_rate)
        
        calculation = Calculation(
            user_id=session['user_id'],
            calculation_type='cost',
            marketplace_id=marketplace.id,
            price=price,
            margin=margin,
            tax_rate=tax_rate,
            result_data=json.dumps({
                "cost": round(cost, 2),
                "shipment": shipment,
                "marketplace_name": marketplace.name
            })
        )
        db.session.add(calculation)
        db.session.commit()
        
        return jsonify({
            "cost": round(cost, 2),
            "shipment": shipment,
            "marketplace_name": marketplace.name
        })
    
    except Exception as e:
        print(f'❌ Erro ao calcular custo: {str(e)}')
        traceback.print_exc()
        return jsonify({"error": "Erro ao calcular custo"}), 500

# ==================== ROTAS DE HISTÓRICO ====================

@app.route('/api/calculations', methods=['GET'])
@admin_required
def get_calculations():
    calculations = Calculation.query.order_by(Calculation.created_at.desc()).limit(100).all()
    return jsonify([calc.to_dict() for calc in calculations])

@app.route('/api/login-history', methods=['GET'])
@admin_required
def get_login_history():
    history = LoginHistory.query.order_by(LoginHistory.created_at.desc()).limit(100).all()
    return jsonify([h.to_dict() for h in history])

# ==================== TRATAMENTO DE ERROS ====================

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint não encontrado"}), 404
    return redirect(url_for('home'))

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({"error": "Erro interno do servidor"}), 500
    return "Erro interno do servidor", 500

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    init_database()
    print('\n' + '='*70)
    print('🚀 SERVIDOR FLASK INICIADO COM SUCESSO!')
    print('='*70)
    print('🌐 URLs Disponíveis:')
    print('   • Página de Teste:    http://localhost:5000/test')
    print('   • Login:              http://localhost:5000/login')
    print('   • Painel (Admin):     http://localhost:5000/painel')
    print('   • Calculadora (User): http://localhost:5000/calculadora')
    print('   • API Marketplaces:   http://localhost:5000/api/marketplaces')
    print('   • API Kits:           http://localhost:5000/api/kits')
    print('')
    print('🔒 Sistema de Autenticação:')
    print('   • Calculadora requer login (user ou admin)')
    print('   • Painel requer login como admin')
    print('   • Usuários inativos são automaticamente deslogados')
    print('')
    print('📦 Marketplaces (ATUALIZADO):')
    print('   ✅ Mercado Livre Premium - 17% - Frete 7/27')
    print('   ✅ Mercado Livre Clássico - 12% - Frete 7/27 (NOVO)')
    print('   ✅ Americanas - Frete 7/27')
    print('   ✅ Magalu - Frete 7/27')
    print('   ✅ Via Varejo - Frete 7/27')
    print('   • Droga Raia - Frete 1.00')
    print('   • Tray - Frete 1.00')
    print('   • Tray + 20% - Frete 1.00')
    print('   • Digigrow - Frete 1.00')
    print('   • Shopee - Frete 4.50')
    print('   • Shopee x2 - Frete 4.50')
    print('')
    print('📊 Banco de Dados: controle_acessos')
    print('👤 Credenciais Padrão:')
    print('   • Admin: admin@sistema.com / admin123')
    print('   • User:  user@sistema.com / user123')
    print('='*70)
    print('💡 Pressione Ctrl+C para parar o servidor')
    print('='*70 + '\n')
    
    app.run(debug=True, port=5000, host='0.0.0.0')