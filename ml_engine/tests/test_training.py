import pytest
import pandas as pd
import os
from unittest.mock import patch
from ml_engine.training import select_best_model, train_and_evaluate_model
from sklearn.linear_model import LogisticRegression

# Create a sample dataset for testing
@pytest.fixture
def sample_data():
    data = {
        'feature1': [i for i in range(20)],
        'feature2': [i * 2 for i in range(20)],
        'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    }
    return pd.DataFrame(data)

# Mock model object for testing the training function
@pytest.fixture
def mock_model():
    # Create a simple mock object that can be passed to the function
    class MockModel:
        pass
    return MockModel()

def test_select_best_model_basic(sample_data):
    """
    Tests that the function runs and returns a model.
    """
    best_model = select_best_model(data=sample_data, target_col='target', sort_by='Accuracy')
    assert best_model is not None
    print(f"Test passed: best_model is not None. Model is: {type(best_model).__name__}")

def test_select_best_model_exclude(sample_data):
    """
    Tests that the exclude parameter works.
    """
    # Exclude Logistic Regression
    best_model = select_best_model(data=sample_data, target_col='target', sort_by='Accuracy', exclude=['lr'])
    assert best_model is not None
    # Check that the returned model is not an instance of LogisticRegression
    assert not isinstance(best_model, LogisticRegression)
    print(f"Test passed: Excluded 'lr' and got {type(best_model).__name__}")

def test_select_best_model_invalid_target(sample_data):
    """
    Tests that a ValueError is raised for an invalid target column.
    """
    with pytest.raises(ValueError):
        select_best_model(data=sample_data, target_col='non_existent_column')

@patch('ml_engine.training.save_model')
@patch('ml_engine.training.predict_model')
@patch('ml_engine.training.finalize_model')
def test_train_and_evaluate_model(mock_finalize, mock_predict, mock_save, mock_model, sample_data):
    """
    Tests the train_and_evaluate_model function, mocking pycaret calls.
    """
    # Configure mocks to return something sensible
    mock_finalize.return_value = 'final_model_object'
    mock_predict.return_value = pd.DataFrame({'prediction_label': [1, 0]})

    # Call the function
    result_path = train_and_evaluate_model(mock_model, sample_data)

    # Assert that the pycaret functions were called
    mock_finalize.assert_called_once_with(mock_model)
    mock_predict.assert_called_once_with('final_model_object', data=sample_data)
    mock_save.assert_called_once()

    # Assert that the returned path is correct
    assert isinstance(result_path, str)
    assert os.path.isabs(result_path)
    assert result_path.endswith('.pkl')