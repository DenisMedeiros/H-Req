import os
import json
import logging

from flask import Flask, url_for, request
from flask import Response

logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
app = Flask(__name__)
script_dir = os.path.dirname(__file__)

@app.route('/', methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
def index():
    logging.info(f"Received a {request.method} request.")
    if request.method == "GET":
        with open(os.path.join(script_dir, "examples", "products.json")) as file:
            body = json.load(file)
    else:
        body = request.json
    response = {
        "description": f"This is a response to a {request.method} request.",
        "request-body": body,
        "request-headers": dict(request.headers),
        "request-parameters": request.args
    }
    response_str = json.dumps(response)
    return Response(response_str, mimetype="application/json")