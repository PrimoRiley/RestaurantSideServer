from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import random
import time
import requests

# Uber Eats API (simplified)
uber_app = Flask(__name__)

# Route for Uber Eats to place an order
@uber_app.route('/uber/order', methods=['POST'])
def uber_create_order():
    data = request.get_json()
    items = data.get('items')
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    response = requests.post('http://127.0.0.1:5000/order', json={'items': items})
    return jsonify(response.json()), response.status_code

# Route for Uber Eats to get the restaurant menu
@uber_app.route('/uber/menu', methods=['GET'])
def uber_get_menu():
    response = requests.get('http://127.0.0.1:5000/menu')
    return jsonify(response.json()), response.status_code

# Route for Uber Eats to provide driver status
@uber_app.route('/uber/driver_status', methods=['GET'])
def uber_driver_status():
    # Simulate driver availability
    driver_available = random.choice([True, False])
    status = 'available' if driver_available else 'unavailable'
    return jsonify({'driver_status': status}), 200

# Route for Uber Eats to provide orders to the restaurant
@uber_app.route('/uber/orders', methods=['GET'])
def uber_get_orders():
    # Simulate orders list
    orders = [
        {'order_id': 1, 'items': 'Pizza, Salad', 'status': 'received', 'timestamp': datetime.now().isoformat()},
        {'order_id': 2, 'items': 'Burger, Fries', 'status': 'preparing', 'timestamp': datetime.now().isoformat()}
    ]
    return jsonify(orders), 200

if __name__ == '__main__':
    uber_app.run(debug=True, port=5001)
