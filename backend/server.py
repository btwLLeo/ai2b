from flask import Flask, request, jsonify

from app import TrentoLogisticsAssistant

# -----------------------------
# INIT APP + MODEL
# -----------------------------
app = Flask(__name__)

# Inizializza UNA SOLA VOLTA all'avvio server
assistant = TrentoLogisticsAssistant(
    qdrant_path="./qdrant_data",
    llm_fn=None  # collega qui il tuo LLM reale
)

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# -----------------------------
# ASK ENDPOINT
# -----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)

    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field"}), 400

    question = data["question"]

    try:
        response = assistant.ask(question)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# SHUTDOWN CLEANUP
# -----------------------------
"""
@app.teardown_appcontext
def shutdown(exception=None):
    try:
        assistant.client.close()
    except Exception:
        pass
"""
# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False  
    )
