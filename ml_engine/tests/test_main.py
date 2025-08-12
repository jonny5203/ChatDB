import pytest
from unittest.mock import patch
import pandas as pd
from ml_engine.main import app

@pytest.fixture
def client():
    return app.test_client()

def test_health_check(client):
    """
    Test the /health endpoint.
    """
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.data == b"OK"

@patch('ml_engine.main.get_sample_data')
def test_preprocess_endpoint(mock_get_sample_data, client):
    """
    Test the /preprocess endpoint with a valid dataset reference.
    """
    # Arrange
    mock_df = pd.DataFrame({
        'age': [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
        'city': ['New York', 'Los Angeles', 'New York', 'Chicago', 'Los Angeles', 'Chicago', 'New York', 'Chicago', 'New York', 'Los Angeles'],
        'income': [50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000],
        'some_text': ['this is a sample text', 'another sample text', 'pycaret is awesome', 'hello world', 'gemini is cool', 'a simple sentence', 'yet another one', 'the quick brown fox', 'jumps over the lazy dog', 'a final sample'],
        'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    })
    mock_get_sample_data.return_value = mock_df
    payload = {"dataset_reference": "juice"}

    # Act
    response = client.post("/preprocess", json=payload)

    # Assert
    assert response.status_code == 200
    response_data = response.get_json()
    assert isinstance(response_data, dict)


@patch('ml_engine.main.get_sample_data')
def test_preprocess_endpoint_invalid_reference(mock_get_sample_data, client):
    """
    Test the /preprocess endpoint with an invalid dataset reference.
    """
    # Arrange
    mock_get_sample_data.return_value = None
    payload = {"dataset_reference": "invalid_dataset"}

    # Act
    response = client.post("/preprocess", json=payload)

    # Assert
    assert response.status_code == 404