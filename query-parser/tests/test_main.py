import pytest
import json
from main import app, MAX_QUERY_SIZE_BYTES

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    rv = client.get('/health')
    assert rv.status_code == 200
    assert b'OK' in rv.data

def test_parse_sql_no_query(client):
    rv = client.post('/parse', json={})
    assert rv.status_code == 400
    response_data = json.loads(rv.data)
    assert response_data['error'] == 'No query provided'

def test_parse_create_model_case_insensitive(client):
    query = "create model my_model options(model_type='logistic_reg') as (select * from my_table)"
    rv = client.post('/parse', json={'query': query})
    print(rv.data)
    assert rv.status_code == 200
    response_data = json.loads(rv.data)
    assert 'create_model' in response_data['ast']

def test_parse_with_semicolon(client):
    query = "SELECT * FROM ML.PREDICT;"
    rv = client.post('/parse', json={'query': query})
    print(rv.data)
    assert rv.status_code == 200
    response_data = json.loads(rv.data)
    assert 'ml_predict' in response_data['ast']

def test_query_size_limit(client):
    long_query = "SELECT " + "a" * (MAX_QUERY_SIZE_BYTES)
    rv = client.post('/parse', json={'query': long_query})
    assert rv.status_code == 400
    response_data = json.loads(rv.data)
    assert response_data['error']['type'] == 'Limit'

def test_invalid_clause_order(client):
    query = "FROM ML.PREDICT(MODEL my_model, (SELECT * FROM new_data)) SELECT *"
    rv = client.post('/parse', json={'query': query})
    assert rv.status_code == 400
    response_data = json.loads(rv.data)
    assert response_data['error']['type'] == 'Syntax'

def test_unsupported_keyword(client):
    query = "ALTER MODEL my_model OPTIONS(model_type='logistic_reg')"
    rv = client.post('/parse', json={'query': query})
    assert rv.status_code == 400
    response_data = json.loads(rv.data)
    assert response_data['error']['type'] == 'Syntax'
