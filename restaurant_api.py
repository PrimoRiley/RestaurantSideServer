from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import random
import time
import requests
import threading

restaurant_app = Flask(__name__)

def init_db():
    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        # Drop existing tables if they exist
        c.execute('DROP TABLE IF EXISTS menu')
        c.execute('DROP TABLE IF EXISTS orders')

        # Create a menu table
        c.execute('''CREATE TABLE IF NOT EXISTS menu (
                     id INTEGER PRIMARY KEY,
                     name TEXT NOT NULL,
                     price REAL NOT NULL,
                     available BOOLEAN NOT NULL DEFAULT 1)''')
        # Create an orders table
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     items TEXT NOT NULL,
                     status TEXT NOT NULL,
                     timestamp TEXT NOT NULL)''')
        
        # Insert realistic test data into the menu table
        menu_items = [
            (1, 'Burger', 8.99, True),
            (2, 'Fries', 2.99, True),
            (3, 'Pizza', 12.99, True),
            (4, 'Salad', 5.49, False),
            (5, 'Chicken Wings', 9.99, True),
            (6, 'Pasta', 11.49, True),
            (7, 'Soda', 1.99, True),
            (8, 'Ice Cream', 3.99, False)
        ]
        c.executemany('INSERT OR IGNORE INTO menu (id, name, price, available) VALUES (?, ?, ?, ?)', menu_items)
        conn.commit()

        # Insert realistic test data into the orders table
        orders = [
            (1, 'Burger, Fries', 'completed', datetime.now().isoformat()),
            (2, 'Pizza', 'preparing', datetime.now().isoformat()),
            (3, 'Chicken Wings, Soda', 'received', datetime.now().isoformat()),
            (4, 'Pasta', 'ready', datetime.now().isoformat())
        ]
        c.executemany('INSERT OR IGNORE INTO orders (id, items, status, timestamp) VALUES (?, ?, ?, ?)', orders)
        conn.commit()

init_db()

# Route to get the menu
@restaurant_app.route('/menu', methods=['GET'])
def get_menu():
    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM menu')
        menu_items = [
            {'id': row[0], 'name': row[1], 'price': row[2], 'available': bool(row[3])}
            for row in c.fetchall()
        ]
    return jsonify(menu_items), 200

# Route to gather orders from Uber Eats API
@restaurant_app.route('/orders', methods=['GET'])
def get_orders():
    response = requests.get('http://127.0.0.1:5001/uber/orders')
    return jsonify(response.json()), response.status_code

# Function to cancel an order after 15 minutes if no driver is available
def cancel_order_if_no_driver(order_id):
    time.sleep(900)  # Wait for 15 minutes
    try:
        with sqlite3.connect('restaurant.db') as conn:
            c = conn.cursor()
            c.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
            result = c.fetchone()
            if result and result[0] == 'received':
                # No driver has picked up the order, cancel it
                c.execute('DELETE FROM orders WHERE id = ?', (order_id,))
                conn.commit()
    except sqlite3.Error as e:
        print(f"Error in cancel_order_if_no_driver: {e}")

# Route to create an order
@restaurant_app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()
    items = data.get('items')
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    item_list = [item.strip() for item in items.split(',')]

    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        # Check if all items are available
        unavailable_items = []
        for item in item_list:
            c.execute('SELECT available FROM menu WHERE name = ?', (item,))
            result = c.fetchone()
            if result is None or result[0] == 0:
                unavailable_items.append(item)

        if unavailable_items:
            return jsonify({'error': f'Item not available.'}), 400

        # Check if a driver is available
        driver_response = requests.get('http://127.0.0.1:5001/uber/driver_status')
        driver_status = driver_response.json().get('driver_status')
        if driver_status != 'available':
            return jsonify({'error': 'No driver available'}), 400

        # Insert order into orders table
        timestamp = datetime.now().isoformat()
        c.execute('INSERT INTO orders (items, status, timestamp) VALUES (?, ?, ?)',
                  (str(items), 'received', timestamp))
        order_id = c.lastrowid
        conn.commit()

        # Start a background thread to cancel the order if no driver is assigned within 15 minutes
        threading.Thread(target=cancel_order_if_no_driver, args=(order_id,)).start()

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
