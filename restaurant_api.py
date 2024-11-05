from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import random
import time
import requests

restaurant_app = Flask(__name__)

# Initialize the SQLite database
def init_db():
    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        # Create a menu table
        c.execute('''CREATE TABLE IF NOT EXISTS menu (
                     id INTEGER PRIMARY KEY,
                     name TEXT NOT NULL,
                     price REAL NOT NULL)''')
        # Create an orders table
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     items TEXT NOT NULL,
                     status TEXT NOT NULL,
                     timestamp TEXT NOT NULL)''')
        conn.commit()

init_db()

# Route to get the menu
@restaurant_app.route('/menu', methods=['GET'])
def get_menu():
    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM menu')
        menu_items = [
            {'id': row[0], 'name': row[1], 'price': row[2]}
            for row in c.fetchall()
        ]
    return jsonify(menu_items), 200

# Route to gather orders from Uber Eats API
@restaurant_app.route('/orders', methods=['GET'])
def get_orders():
    response = requests.get('http://127.0.0.1:5001/uber/orders')
    return jsonify(response.json()), response.status_code

# Route to create an order
@restaurant_app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()
    items = data.get('items')
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    # Check if a driver is available before creating the order
    response = requests.get('http://127.0.0.1:5001/uber/driver_status')
    driver_status = response.json().get('driver_status')
    if driver_status != 'available':
        return jsonify({'error': 'No driver available'}), 400

    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute('INSERT INTO orders (items, status, timestamp) VALUES (?, ?, ?)',
                  (str(items), 'received', timestamp))
        order_id = c.lastrowid
        conn.commit()

    return jsonify({'order_id': order_id, 'status': 'received'}), 201

# Route to update an order's status
@restaurant_app.route('/order/<int:order_id>', methods=['PATCH'])
def update_order(order_id):
    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['received', 'preparing', 'ready', 'completed']

    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        c.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
        if c.rowcount == 0:
            return jsonify({'error': 'Order not found'}), 404
        conn.commit()

    return jsonify({'order_id': order_id, 'new_status': new_status}), 200

if __name__ == '__main__':
    restaurant_app.run(debug=True, port=5000)
