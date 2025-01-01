from flask import Flask, request, jsonify
from prometheus_client import Counter, Summary, generate_latest, CONTENT_TYPE_LATEST
import subprocess
import time

app = Flask(__name__)

# Metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
REQUEST_LATENCY = Summary('request_latency_seconds', 'Request latency', ['endpoint', 'method'])
START_TIME = time.time()

# Path to the DNS management script
DNS_SCRIPT_PATH = "./hello-world.py"

# Helper function to run the DNS script
def run_dns_script(action, params):
    command = ["python", DNS_SCRIPT_PATH, action] + [f"--{k}={v}" for k, v in params.items()]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return "success", result.stdout
    except subprocess.CalledProcessError as e:
        return "error", e.stderr

@app.route('/dns/<action>', methods=['POST'])
def dns_action(action):
    """
    Handle DNS actions (create or delete).
    """
    with REQUEST_LATENCY.labels(endpoint='/dns', method='POST').time():
        if action not in ["create", "delete"]:
            REQUEST_COUNT.labels(endpoint='/dns', method='POST', status='400').inc()
            return jsonify({"error": "Invalid action"}), 400

        data = request.json
        if not data:
            REQUEST_COUNT.labels(endpoint='/dns', method='POST', status='400').inc()
            return jsonify({"error": "No data provided"}), 400

        status, output = run_dns_script(action, data)

        if status == "success":
            REQUEST_COUNT.labels(endpoint='/dns', method='POST', status='200').inc()
            return jsonify({"message": f"DNS {action} completed successfully", "details": output}), 200
        else:
            REQUEST_COUNT.labels(endpoint='/dns', method='POST', status='500').inc()
            return jsonify({"error": f"Failed to {action} DNS record", "details": output}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Expose Prometheus metrics.
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint to verify API availability.
    """
    # Optional: Add checks like file existence, etc.
    return jsonify({"status": "healthy", "uptime_seconds": time.time() - START_TIME}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
