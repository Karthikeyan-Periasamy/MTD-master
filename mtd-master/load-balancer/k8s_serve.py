from flask import Flask, request
import requests as req
from improved_k8s_controller import KubernetesController
from markupsafe import escape

app = Flask("kubernetes load balancer")
controller = KubernetesController()

@app.route("/", defaults={"path": ""}, methods=["GET", "PUT", "POST"])
@app.route("/<path:path>", methods=["GET", "PUT", "POST"])
def route(path):
    try:
        # Get a random pod from our controller
        app_instance = controller.random_app()
        url = f"http://{app_instance.pod_ip}:8080/{path}"
        
        app.logger.info(f"Routing to {url}")
        
        # Forward the request to the selected pod
        response = req.request(
            method=request.method,
            url=url,
            headers={key: value for key, value in request.headers if key != 'Host'},
            cookies=request.cookies,
            data=request.get_data(),
            params=request.args
        )
        
        # Return the response from the pod
        return response.text, response.status_code, response.headers.items()
    
    except Exception as e:
        app.logger.error(f"Error routing request: {e}")
        return {"error": "Internal server error"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
