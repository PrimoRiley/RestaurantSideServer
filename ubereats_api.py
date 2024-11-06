from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import random
import time
import requests

# Uber Eats API (simplified)
uber_app = Flask(__name__)

# Route for Uber Eats to provide driver status
@uber_app.route('/uber/driver_status', methods=['GET'])
def uber_driver_status():
    # Simulate driver availability
    driver_available = random.choice([True, False])
    status = 'available' if driver_available else 'unavailable'
    return jsonify({'driver_status': status}), 200

# Route for Uber Eats to update order status
@uber_app.route('/uber/order/<int:order_id>', methods=['PATCH'])
def uber_update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['received', 'preparing', 'ready', 'completed']

    # Check if the new status is valid
    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    return jsonify({'order_id': order_id, 'new_status': new_status}), 200

if __name__ == '__main__':
    uber_app.run(debug=True, port=5001)
