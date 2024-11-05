import unittest
import threading
import requests
import time
from restaurant_api import restaurant_app, init_db
from ubereats_api import uber_app
from unittest import mock

class TestRestaurantUberEatsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the restaurant app server
        init_db()
        cls.restaurant_thread = threading.Thread(target=restaurant_app.run, kwargs={'port': 5000, 'debug': False, 'use_reloader': False})
        cls.restaurant_thread.setDaemon(True)  # Ensure the server thread exits when the main thread does
        cls.restaurant_thread.start()

        # Start the Uber Eats app server
        cls.uber_thread = threading.Thread(target=uber_app.run, kwargs={'port': 5001, 'debug': False, 'use_reloader': False})
        cls.uber_thread.setDaemon(True)
        cls.uber_thread.start()

        # Give the servers a moment to start
        time.sleep(2)

    def test_place_order_success(self):
        """ Test placing a successful order via Uber Eats """
        # Mock driver status response to simulate driver availability
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'driver_status': 'available'}
            mock_get.return_value.status_code = 200

            # Place an order via Uber Eats
            response = requests.post('http://127.0.0.1:5001/uber/order', json={'items': 'Burger, Fries'})
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertIn('order_id', data)

    @mock.patch('time.sleep', return_value=None)  # Instantly returns simulating the full timeout.
    @mock.patch('sqlite3.connect')
    def test_order_cancellation_after_no_driver(self, mock_connect, mock_sleep):
        """ Test that the order is canceled after 15 minutes if no driver is available """
        
        # Mock database connection and cursor
        mock_conn = mock.Mock()
        mock_cursor = mock.Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock driver status response to simulate driver unavailability
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'driver_status': 'unavailable'}
            mock_get.return_value.status_code = 200

            # Place an order with no driver available
            response = requests.post('http://127.0.0.1:5000/order', json={'items': 'Burger, Fries'})
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json())
            self.assertEqual(response.json()['error'], 'No driver available at the moment')

            # Check that sleep was called for 15 minutes
            mock_sleep.assert_called_once_with(900)

            # Check that the order was deleted from the database
            mock_cursor.execute.assert_any_call('DELETE FROM orders WHERE id = ?', mock.ANY)


    def test_place_order_invalid_item(self):
        """ Test placing an order with unavailable items """
        response = requests.post('http://127.0.0.1:5001/uber/order', json={'items': 'Invalid Item'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'Item not available.')

    def test_create_order_missing_items(self):
        """ Test creating an order with missing items """
        response = requests.post('http://127.0.0.1:5000/order', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'No items provided')

    @mock.patch('requests.get', return_value=mock.Mock(json=lambda: {'driver_status': 'available'}, status_code=200))
    def test_update_order_status_success(self, mock_get):
        """ Test updating an order's status successfully """
        # Create an order
        response = requests.post('http://127.0.0.1:5000/order', json={'items': 'Pizza'})
        self.assertEqual(response.status_code, 201)
        order_id = response.json()['order_id']

        # Update status to 'preparing'
        response = requests.patch(f'http://127.0.0.1:5000/order/{order_id}', json={'status': 'preparing'})
        self.assertEqual(response.status_code, 200)
        
        # Verify Uber Eats received the status update by getting the orders list
        response = requests.get('http://127.0.0.1:5001/uber/orders')
        orders = response.json()
        order_status = next((order for order in orders if order['order_id'] == order_id), None)
        self.assertIsNotNone(order_status)
        self.assertEqual(order_status['status'], 'preparing')

    def test_update_order_status_invalid(self):
        """ Test updating an order with an invalid status """
        # Create an order
        response = requests.post('http://127.0.0.1:5000/order', json={'items': 'Pizza'})
        self.assertEqual(response.status_code, 201)
        order_id = response.json()['order_id']

        # Attempt to update to an invalid status
        response = requests.patch(f'http://127.0.0.1:5000/order/{order_id}', json={'status': 'invalid_status'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'Invalid status')

    def test_update_non_existent_order(self):
        """ Test updating a non-existent order """
        response = requests.patch('http://127.0.0.1:5000/order/999', json={'status': 'preparing'})
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'Order not found')

    def test_get_orders_from_uber(self):
        """ Test getting orders from Uber Eats via restaurant server """
        response = requests.get('http://127.0.0.1:5000/orders')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_driver_availability(self):
        """ Test checking driver availability """
        response = requests.get('http://127.0.0.1:5001/uber/driver_status')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data['driver_status'], ['available', 'unavailable'])

    @classmethod
    def tearDownClass(cls):
        # The daemon threads will automatically stop when the main thread ends
        pass

if __name__ == '__main__':
    unittest.main()
