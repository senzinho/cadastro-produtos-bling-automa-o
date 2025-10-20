from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configurações dos marketplaces
MARKETPLACES = [
    {"id": 0, "name": "Mercado Livre", "commission": 0.12},
    {"id": 1, "name": "Americanas", "commission": 0.16},
    {"id": 2, "name": "Magalu", "commission": 0.18},
    {"id": 3, "name": "Via Varejo", "commission": 0.17},
    {"id": 4, "name": "Droga Raia", "commission": 0.22},
    {"id": 5, "name": "Tray", "commission": 0.05},
    {"id": 6, "name": "Tray + 20%", "commission": 0.05},
    {"id": 7, "name": "Digigrow", "commission": 0.18},
    {"id": 8, "name": "Shopee", "commission": 0.20},
    {"id": 9, "name": "Shopee x2", "commission": 0.20}
]

# Configurações dos kits
KIT_CONFIGS = [
    {
        "id": 0,
        "name": "Kits de 2, 3 e 6",
        "kits": [
            {"name": "Kit 2", "multiplier": 2},
            {"name": "Kit 3", "multiplier": 3},
            {"name": "Kit 6", "multiplier": 6}
        ]
    },
    {
        "id": 1,
        "name": "Kits de 4, 12 e 24",
        "kits": [
            {"name": "Kit 4", "multiplier": 4},
            {"name": "Kit 12", "multiplier": 12},
            {"name": "Kit 24", "multiplier": 24}
        ]
    },
    {
        "id": 2,
        "name": "Kits de 5, 10 e 20",
        "kits": [
            {"name": "Kit 5", "multiplier": 5},
            {"name": "Kit 10", "multiplier": 10},
            {"name": "Kit 20", "multiplier": 20}
        ]
    },
    {
        "id": 3,
        "name": "Kits de 8, 16 e 18",
        "kits": [
            {"name": "Kit 8", "multiplier": 8},
            {"name": "Kit 16", "multiplier": 16},
            {"name": "Kit 18", "multiplier": 18}
        ]
    }
]

def get_shipment_value(marketplace_id, price=0):
    """Calcula o valor do frete baseado no marketplace e preço"""
    if marketplace_id >= 4 and marketplace_id <= 7:
        return 1.0
    elif marketplace_id in [8, 9]:  # Shopee
        return 4.5
    else:
        # Para marketplaces 0-3, se preço >= 78, frete é 22
        if price >= 78:
            return 22.0
        return 6.0

def calculate_price(cost, margin, marketplace_id, tax_rate, kit_amt=1):
    """Calcula o preço de venda baseado no custo"""
    commission = MARKETPLACES[marketplace_id]["commission"]
    
    # Primeira tentativa com frete inicial
    shipment = get_shipment_value(marketplace_id, 0)
    price = ((cost * (margin * 0.01 + 1) * kit_amt) + shipment) / (1 - (commission + tax_rate))
    
    # Se for marketplace 0-3 e preço >= 78, recalcula com frete maior
    if marketplace_id <= 3 and price >= 78:
        shipment = 22.0
        price = ((cost * (margin * 0.01 + 1) * kit_amt) + shipment) / (1 - (commission + tax_rate))
    
    # Ajustes especiais
    if marketplace_id == 9:  # Shopee x2
        price *= 2
    elif marketplace_id == 6:  # Tray + 20%
        price = ((price / (1 - 0.10)) / (1 - 0.10))
    
    return price, shipment

def calculate_cost(price, margin, marketplace_id, tax_rate):
    """Calcula o custo baseado no preço de venda"""
    commission = MARKETPLACES[marketplace_id]["commission"]
    
    # Primeira tentativa com frete inicial
    shipment = get_shipment_value(marketplace_id, 0)
    cost = (price - (price * (commission + tax_rate)) - shipment) / (1 + margin * 0.01)
    
    # Se for marketplace 0-3 e preço >= 78, recalcula com frete maior
    if marketplace_id <= 3 and price >= 78:
        shipment = 22.0
        cost = (price - (price * (commission + tax_rate)) - shipment) / (1 + margin * 0.01)
    
    return cost, shipment

@app.route('/api/marketplaces', methods=['GET'])
def get_marketplaces():
    """Retorna lista de marketplaces"""
    return jsonify(MARKETPLACES)

@app.route('/api/kits', methods=['GET'])
def get_kits():
    """Retorna configurações de kits"""
    return jsonify(KIT_CONFIGS)

@app.route('/api/calculate-all-prices', methods=['POST'])
def calculate_all_prices():
    """Calcula preço de venda para TODOS os marketplaces"""
    data = request.json
    cost = float(data.get('cost', 0))
    margin = float(data.get('margin', 20))
    tax_rate = float(data.get('tax_rate', 0.1))
    kit_config_id = int(data.get('kit_config_id', 0))
    
    if cost <= 0:
        return jsonify({"error": "Custo deve ser maior que zero"}), 400
    
    kit_config = KIT_CONFIGS[kit_config_id]
    all_results = []
    
    # Calcula para cada marketplace
    for marketplace in MARKETPLACES:
        marketplace_id = marketplace["id"]
        commission = marketplace["commission"]
        
        # Calcula para unidade única
        single_price, shipment = calculate_price(cost, margin, marketplace_id, tax_rate, 1)
        
        # Calcula comissão e imposto apenas para unidade única
        only_commission = single_price * commission
        only_tax = single_price * tax_rate
        profit = cost * (margin * 0.01)
        
        # Calcula para cada kit
        kits_prices = []
        for kit in kit_config["kits"]:
            kit_price, _ = calculate_price(cost, margin, marketplace_id, tax_rate, kit["multiplier"])
            kits_prices.append({
                "name": kit["name"],
                "multiplier": kit["multiplier"],
                "price": round(kit_price, 2)
            })
        
        all_results.append({
            "marketplace_id": marketplace_id,
            "marketplace_name": marketplace["name"],
            "single_price": round(single_price, 2),
            "kits": kits_prices,
            "shipment": shipment if marketplace_id > 3 else "6.00 ou 22.00",
            "commission": round(only_commission, 2),
            "tax": round(only_tax, 2),
            "profit": round(profit, 2)
        })
    
    return jsonify({
        "results": all_results,
        "kit_config_name": kit_config["name"]
    })

@app.route('/api/calculate-cost', methods=['POST'])
def calculate_cost_endpoint():
    """Calcula custo baseado no preço de venda"""
    data = request.json
    price = float(data.get('price', 0))
    margin = float(data.get('margin', 20))
    tax_rate = float(data.get('tax_rate', 0.1))
    marketplace_id = int(data.get('marketplace_id', 0))
    
    if price <= 0:
        return jsonify({"error": "Preço deve ser maior que zero"}), 400
    
    cost, shipment = calculate_cost(price, margin, marketplace_id, tax_rate)
    
    return jsonify({
        "cost": round(cost, 2),
        "shipment": shipment,
        "marketplace_name": MARKETPLACES[marketplace_id]["name"]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)