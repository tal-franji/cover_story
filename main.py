import os
import io
import numpy as np
import cv2
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from cv_engine import process_screenshot
from solver_engine import solve_puzzle
import base64

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Use a temporary directory for uploaded images
UPLOAD_FOLDER = '/tmp/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    img_path = os.path.join(UPLOAD_FOLDER, "current_scan.jpg")
    file.save(img_path)
    
    result = process_screenshot(img_path)
    if not result:
        return jsonify({"error": "Could not detect game data in image"}), 422
    
    # Also return the uploaded image as base64 for preview/overlay
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        result['image_b64'] = encoded_string
    
    return jsonify(result)

@app.route('/solve', methods=['POST'])
def solve():
    try:
        data = request.json
        grid = data.get('grid')
        pieces = data.get('pieces')
        
        if grid is None or pieces is None:
            return jsonify({"error": "Missing grid or pieces data"}), 400
        
        print(f"Solving with {len(pieces)} pieces and {len(grid)}x{len(grid[0])} grid")
        solution = solve_puzzle(grid, pieces)
        if not solution:
            return jsonify({"error": "No solution found. Check if grid colors or piece shapes are correct."}), 404
            
        return jsonify({"solution": solution})
    except Exception as e:
        print(f"Solver error: {str(e)}")
        return jsonify({"error": f"Internal solver error: {str(e)}"}), 500

if __name__ == '__main__':
    # For local development
    app.run(host='0.0.0.0', port=8080, debug=True)
