from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import time
import requests
import threading

restaurant_app = Flask(__name__)

# Route: Provide Menu to Uber
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


# Function to cancel an order after 15 minutes if no driver is available
def cancel_order_if_no_driver(order_id):
    try:
        with sqlite3.connect('restaurant.db') as conn:
            c = conn.cursor()
            c.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
            result = c.fetchone()
            if result and result[0] == 'received':
                # Delete unconfirmed order
                c.execute('DELETE FROM orders WHERE id = ?', (order_id,))
                conn.commit()
    except sqlite3.Error as e:
        print(f"Error in cancel_order_if_no_driver: {e}")

# Function to update order status if a driver becomes available
def update_order_status_to_preparing(order_id):
    try:
        with sqlite3.connect('restaurant.db') as conn:
            c = conn.cursor()
            c.execute('UPDATE orders SET status = ? WHERE id = ?', ('preparing', order_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error in update_order_status_to_preparing: {e}")

# Function to start the background thread to monitor driver availability and cancel the order if needed
def monitor_driver_availability(order_id):
    start_time = time.time()
    while time.time() - start_time < 3:  # Originally meant for up to 15 minutes but instead put at 3 for testing
        driver_response = requests.get('http://127.0.0.1:5001/uber/driver_status')
        if driver_response.status_code == 200:
            driver_status = driver_response.json().get('driver_status')
            if driver_status == 'available':
                update_order_status_to_preparing(order_id)
                return
        # time.sleep(30)  # Orignally meant to check every 30 seconds but adjusted for testing purposes
    cancel_order_if_no_driver(order_id)

# Route: Let Uber Interact with to create order 
@restaurant_app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()
    items = data.get('items')
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    try:
        if isinstance(items, str):
            items = [item.strip() for item in items.split(',')]

        # Check menu
        try:
            with sqlite3.connect('restaurant.db') as conn:
                c = conn.cursor()
                unavailable_items = []
                for item in items:
                    c.execute('SELECT available FROM menu WHERE name = ?', (item,))
                    result = c.fetchone()
                    if result is None or result[0] == 0:
                        unavailable_items.append(item)

                if unavailable_items:
                    return jsonify({'error': f'Item(s) not available: {", ".join(unavailable_items)}'}), 400
        except sqlite3.Error as e:
            return jsonify({'error': f'Failed to create order: {e}'}), 500
        
        try:
            # Create order
            with sqlite3.connect('restaurant.db') as conn:
                c = conn.cursor()
                timestamp = datetime.now().isoformat()
                c.execute('INSERT INTO orders (items, status, timestamp) VALUES (?, ?, ?)',
                        (str(items), 'received', timestamp))
                order_id = c.lastrowid
                conn.commit()
        except sqlite3.Error as e:
            return jsonify({'error': f'Failed to create order: {e}'}), 500
        
        # Start a background thread to monitor driver availability and cancel the order if needed
        threading.Thread(target=monitor_driver_availability, args=(order_id,)).start()

        return jsonify({'order_id': order_id, 'status': 'received'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Route: Get an order by ID
@restaurant_app.route('/order/<int:order_id>', methods=['GET'])
def get_order_status(order_id):
    try:
        with sqlite3.connect('restaurant.db') as conn:
            c = conn.cursor()
            c.execute('SELECT items, status, timestamp FROM orders WHERE id = ?', (order_id,))
            result = c.fetchone()  
    except sqlite3.Error as e:
        return jsonify({'error': f'Failed to retrieve order: {e}'}), 500

    if result is None:
        return jsonify({'error': 'Order not found'}), 404
    
    items, status, timestamp = result
    
    return jsonify({
        'order_id': order_id,
        'items': items,
        'status': status,
        'timestamp': timestamp
    }), 200


# Route: Update an order's status (Restaurant only)
@restaurant_app.route('/order/<int:order_id>', methods=['PATCH'])
def update_order(order_id):
    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['received', 'preparing', 'ready', 'completed']

    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    try:
        with sqlite3.connect('restaurant.db') as conn:
            c = conn.cursor()
            c.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
            if c.rowcount == 0:
                return jsonify({'error': 'Order not found'}), 404
            conn.commit()
    except sqlite3.Error as e:
        return jsonify({'error': f'Failed to update order: {e}'}), 500


    try:
        response = requests.patch(f'http://localhost:5001/uber/order/{order_id}', json={'status': new_status})
        response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({'error': f'Failed to update Uber Eats: {str(e)}'}), 500

    return jsonify({'order_id': order_id, 'new_status': new_status}), 200

if __name__ == '__main__':
    restaurant_app.run(debug=True, port=5000)
