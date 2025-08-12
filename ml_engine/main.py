from flask import Flask, jsonify
from ml_engine.preprocessing import get_sample_data, run_preprocessing_pipeline

app = Flask(__name__)

@app.route("/health")
def health():
    return "OK"

@app.route("/preprocess", methods=["POST"])
def preprocess_data():
    df = get_sample_data()
    if df is None:
        return jsonify({"detail": "Dataset not found"}), 404
    processed_df = run_preprocessing_pipeline(df, target='target')
    return jsonify(processed_df.to_dict())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
