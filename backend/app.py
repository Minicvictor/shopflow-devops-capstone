import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import redis

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql+psycopg2://shopflow:shopflow@localhost:5432/shopflow')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
cache = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(40), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

@app.get('/')
def index():
    return jsonify(application='ShopFlow API', version='1.0.0', message='Welcome to ShopFlow')

@app.get('/health')
def health():
    return jsonify(status='healthy'), 200

@app.get('/ready')
def readiness():
    try:
        db.session.execute(db.text('SELECT 1'))
        cache.ping()
        return jsonify(status='ready', database='ok', redis='ok'), 200
    except Exception as exc:
        return jsonify(status='not_ready', error=str(exc)), 503

@app.get('/api/products')
def get_products():
    products = Product.query.order_by(Product.id.desc()).all()
    return jsonify([{'id': p.id, 'name': p.name, 'description': p.description, 'price': p.price, 'stock': p.stock} for p in products])

@app.post('/api/products')
def create_product():
    data = request.get_json(silent=True) or {}
    missing = [f for f in ['name', 'price', 'stock'] if f not in data]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400
    try:
        product = Product(name=str(data['name']).strip(), description=str(data.get('description', '')).strip(), price=float(data['price']), stock=int(data['stock']))
        if not product.name or product.price < 0 or product.stock < 0:
            raise ValueError
        db.session.add(product)
        db.session.commit()
        return jsonify(id=product.id, name=product.name, price=product.price, stock=product.stock), 201
    except (TypeError, ValueError):
        db.session.rollback()
        return jsonify(error='Invalid product data'), 400

@app.post('/api/orders')
def create_order():
    data = request.get_json(silent=True) or {}
    try:
        product_id, quantity = int(data['product_id']), int(data['quantity'])
        if quantity <= 0: raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify(error='product_id and a positive quantity are required'), 400
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify(error='Product not found'), 404
    if product.stock < quantity:
        return jsonify(error='Insufficient stock'), 409
    product.stock -= quantity
    order = Order(product_id=product.id, quantity=quantity, total=round(product.price * quantity, 2), status='confirmed')
    db.session.add(order)
    db.session.commit()
    return jsonify(order_id=order.id, product_id=product.id, quantity=quantity, total=order.total, status=order.status), 201

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized.')

@app.cli.command('seed')
def seed():
    db.create_all()
    if Product.query.count() > 0:
        print('Products already exist; nothing to seed.')
        return
    db.session.add_all([
        Product(name='Mechanical Keyboard', description='Compact mechanical keyboard for developers.', price=75000, stock=25),
        Product(name='Wireless Mouse', description='Ergonomic wireless mouse.', price=35000, stock=40),
        Product(name='USB-C Hub', description='Multi-port USB-C hub for laptops.', price=45000, stock=30),
    ])
    db.session.commit()
    print('Sample products inserted.')

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')))
