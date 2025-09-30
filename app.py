from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
CORS(app, resources={r"/v1/*": {"origins": "*"}})

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

# Helper to safely hash values
def sha256_hash(value) -> str:
    if value is None:
        value = ""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # Convert submission to dict for modification
    submission_data = submission.dict()

    # Exercise 2: Hash email and age
    submission_data["email"] = sha256_hash(submission_data.get("email"))
    submission_data["age"] = sha256_hash(submission_data.get("age"))

    # Exercise 1: Set user_agent from payload if missing
    if not submission_data.get("user_agent"):
        submission_data["user_agent"] = request.headers.get("User-Agent", "")

    # Exercise 3: Generate submission_id if missing
    if not submission_data.get("submission_id"):
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        submission_data["submission_id"] = sha256_hash(submission_data["email"] + now_str)

    # Create stored record and append to file
    record = StoredSurveyRecord(
        **submission_data,
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )
    append_json_line(record.dict())

    return jsonify({"status": "ok"}), 201


if __name__ == "__main__":
    app.run(port=5000, debug=True)

