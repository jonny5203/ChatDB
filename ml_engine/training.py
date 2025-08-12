import pandas as pd
from pycaret.classification import setup, compare_models, pull, finalize_model, predict_model, save_model
from datetime import datetime
import os

def select_best_model(data: pd.DataFrame, target_col: str, sort_by: str = 'Accuracy', exclude: list = None):
    """
    Initializes PyCaret setup, compares all models, and returns the best one.
    Handles cases where no model is returned.
    """
    print("Initializing PyCaret setup...")
    # Setup the environment
    # Setting fold=3 due to small sample size in tests.
    setup(data=data, target=target_col, fold=3)

    print(f"Comparing models, sorting by {sort_by}...")
    # Compare models
    best_model = compare_models(sort=sort_by, exclude=exclude)

    print("Model Comparison Results:")
    # Pull the results grid
    results_grid = pull()
    print(results_grid)

    # compare_models can return a list if no single best model is found
    if isinstance(best_model, list) and not best_model:
        print("Warning: compare_models returned an empty list. No model was selected.")
        return None

    return best_model

def train_and_evaluate_model(model, data: pd.DataFrame):
    """
    Trains the final model on the full dataset, evaluates it, and saves the artifact.

    :param model: A trained model object from PyCaret.
    :param data: The full dataset for training and evaluation.
    :return: The absolute file path to the saved model artifact.
    """
    print("Finalizing the model...")
    final_model = finalize_model(model)

    print("Evaluating the final model...")
    predictions = predict_model(final_model, data=data)
    # Displaying the last few rows with predictions
    print(predictions.tail())

    # Define the output directory for models
    output_dir = os.path.abspath("ml_engine/models")
    os.makedirs(output_dir, exist_ok=True)

    # Generate a unique filename with a timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = "final_model"
    file_name = f"{model_name}_{timestamp}"
    
    # Construct the full absolute path
    full_path = os.path.join(output_dir, file_name)
    
    print(f"Saving model to {full_path}.pkl")
    # PyCaret automatically appends .pkl, so we pass the path without the extension
    save_model(final_model, full_path)

    return f"{full_path}.pkl"