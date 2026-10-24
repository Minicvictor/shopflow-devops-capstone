import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
from app import app, db

def test_health():
    client = app.test_client()
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'healthy'

def test_create_and_list_product():
    with app.app_context():
        db.drop_all(); db.create_all()
    client = app.test_client()
    response = client.post('/api/products', json={'name':'Test Product','description':'Test','price':100,'stock':10})
    assert response.status_code == 201
    response = client.get('/api/products')
    assert response.status_code == 200
    assert len(response.get_json()) == 1
