import pandas as pd
from pycaret.classification import setup
from typing import List, Optional

def get_sample_data() -> pd.DataFrame:
    # In a real scenario, this would connect to the DB Connector
    # For now, we'll create a sample DataFrame
    data = {
        'age': [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
        'city': ['New York', 'Los Angeles', 'New York', 'Chicago', 'Los Angeles', 'Chicago', 'New York', 'Chicago', 'New York', 'Los Angeles'],
        'income': [50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000],
        'some_text': ['this is a sample text', 'another sample text', 'pycaret is awesome', 'hello world', 'gemini is cool', 'a simple sentence', 'yet another one', 'the quick brown fox', 'jumps over the lazy dog', 'a final sample'],
        'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    }
    return pd.DataFrame(data)

def run_preprocessing_pipeline(
    df: pd.DataFrame,
    target: str,
    categorical_features: Optional[List[str]] = None,
    numeric_features: Optional[List[str]] = None,
    pca: bool = False,
    polynomial_features: bool = False,
    remove_outliers: bool = False
) -> pd.DataFrame:
    # Setting up the pycaret environment
    if categorical_features is None:
        categorical_features = []

    s = setup(data=df, target=target, session_id=123,
              categorical_features=categorical_features,
              numeric_features=numeric_features,
              pca=pca,
              polynomial_features=polynomial_features,
              remove_outliers=remove_outliers,
              normalize=True,
              transformation=False  # Keep original scale, just normalize
            )

    # The setup function returns a ClassificationExperiment object
    return s.X_train_transformed
