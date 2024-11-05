import unittest
import threading
import requests
import time
from restaurant_api import restaurant_app
from ubereats_api import uber_app

class TestRestaurantUberEatsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the restaurant app server
        cls.restaurant_thread = threading.Thread(target=restaurant_app.run, kwargs={'port': 5000, 'debug': False, 'use_reloader': False})
        cls.restaurant_thread.setDaemon(True)  # Ensure the server thread exits when the main thread does
        cls.restaurant_thread.start()

        # Start the Uber Eats app server
        cls.uber_thread = threading.Thread(target=uber_app.run, kwargs={'port': 5001, 'debug': False, 'use_reloader': False})
        cls.uber_thread.setDaemon(True)
        cls.uber_thread.start()

        # Give the servers a moment to start
        time.sleep(2)

    def test_place_order(self):
        # Place an order via Uber Eats
        response = requests.post('http://127.0.0.1:5001/uber/order', json={'items': 'Burger, Fries'})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('order_id', data)

    def test_get_orders_from_uber(self):
        # Get orders from Uber Eats via restaurant server
        response = requests.get('http://127.0.0.1:5000/orders')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_driver_availability(self):
        # Check driver availability
        response = requests.get('http://127.0.0.1:5001/uber/driver_status')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data['driver_status'], ['available', 'unavailable'])

    def test_order_status_update(self):
        # Create an order via restaurant API
        response = requests.post('http://127.0.0.1:5000/order', json={'items': 'Pizza'})
        self.assertEqual(response.status_code, 201)
        order_id = response.json()['order_id']

        # Update status to 'preparing'
        response = requests.patch(f'http://127.0.0.1:5000/order/{order_id}', json={'status': 'preparing'})
        self.assertEqual(response.status_code, 200)
        
        # Verify Uber Eats has received the status update by getting the orders list
        response = requests.get('http://127.0.0.1:5001/uber/orders')
        orders = response.json()
        order_status = next((order for order in orders if order['order_id'] == order_id), None)
        self.assertIsNotNone(order_status)
        self.assertEqual(order_status['status'], 'preparing')

    @classmethod
    def tearDownClass(cls):
        # If needed, you could add logic to stop the server threads here
        # Since they are daemon threads, they will stop when the main thread stops
        pass

if __name__ == '__main__':
    unittest.main()
