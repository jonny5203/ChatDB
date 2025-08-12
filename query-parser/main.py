from flask import Flask, request, jsonify
import sqlparse
import re
import logging
from custom_parser import custom_sql_parser, ValidationError

import logging

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

MAX_QUERY_SIZE_BYTES = 1 * 1024 * 1024  # 1MB

@app.route("/health")
def health():
    return "OK"

@app.route("/parse", methods=["POST"])
def parse_sql():
    if request.content_length > MAX_QUERY_SIZE_BYTES:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "type": "Limit",
                "message": f"Query size exceeds the limit of {MAX_QUERY_SIZE_BYTES} bytes."
            }
        }), 400

    query = request.json.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    app.logger.debug(f"Query before parsing: {query}")

    try:
        parsed = custom_sql_parser.parse(query)
        return jsonify({"ast": parsed})
    except ValidationError as e:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "type": e.error_type,
                "message": str(e),
                "details": e.details
            }
        }), 400
    except Exception as e:
        # Fallback for syntax errors not caught by the custom parser
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "type": "Syntax",
                "message": "Invalid syntax.",
                "details": {"lark_error": str(e)}
            }
        }), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
