import unittest
import requests
import threading
import time
from unittest.mock import patch
from restaurant_api import restaurant_app
from restaurant_db import init_db
from ubereats_api import uber_app

def mock_driver_response(url, *args, **kwargs):
    if '/uber/driver_status' in url:
        return type('Response', (object,), {
            "status_code": 200, 
            "json": lambda *args, **kwargs: {'driver_status': 'available'}
        })()
    raise RuntimeError("Unhandled URL: " + url)

def time_progression(start_time, increment=300):
        """
        Generator that simulates time progression.
        Each call to time.time() will increment time by the given increment.
        """
        current_time = start_time
        while True:
            yield current_time
            current_time += increment


class TestRestaurantUberEatsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()  # Ensure fresh DB for each test run
        cls.restaurant_thread = threading.Thread(target=restaurant_app.run, kwargs={'port': 5000, 'debug': False, 'use_reloader': False})
        cls.restaurant_thread.setDaemon(True)  # Ensure the server thread exits when the main thread does
        cls.restaurant_thread.start()

        cls.uber_thread = threading.Thread(target=uber_app.run, kwargs={'port': 5001, 'debug': False, 'use_reloader': False})
        cls.uber_thread.setDaemon(True)
        cls.uber_thread.start()

        # Give servers a moment to start
        time.sleep(2)

    def test_get_menu(self):
        response = requests.get('http://127.0.0.1:5000/menu')
        self.assertEqual(response.status_code, 200)
        menu_items = response.json()
        self.assertIsInstance(menu_items, list)
        self.assertGreater(len(menu_items), 0)
        for item in menu_items:
            self.assertIn('id', item)
            self.assertIn('name', item)
            self.assertIn('price', item)
            self.assertIn('available', item)

    @patch('requests.get', side_effect=mock_driver_response)
    def test_create_order_success(self, mock_get):
        payload = {'items': 'Burger, Fries'}
        response = requests.post('http://127.0.0.1:5000/order', json=payload)
        self.assertEqual(response.status_code, 201)
        order_data = response.json()
        self.assertIn('order_id', order_data)
        self.assertEqual(order_data['status'], 'received')

    def test_create_order_item_not_available(self):
        payload = {'items': 'Ice Cream'}  # Ice Cream is marked as unavailable in the DB
        response = requests.post('http://127.0.0.1:5000/order', json=payload)
        self.assertEqual(response.status_code, 400)
        error_message = response.json().get('error')
        self.assertIn('Item(s) not available', error_message)

    def test_create_order_invalid_items(self):
        payload = {'items': 'Nonexistent Item'}
        response = requests.post('http://127.0.0.1:5000/order', json=payload)
        self.assertEqual(response.status_code, 400)
        error_message = response.json().get('error')
        self.assertIn('Item(s) not available', error_message)

    def test_get_order_status_success(self):
        order_id = 1
        response = requests.get(f'http://127.0.0.1:5000/order/{order_id}')
        self.assertEqual(response.status_code, 200)
        order_status = response.json()
        self.assertEqual(order_status['order_id'], order_id)
        self.assertEqual(order_status['status'], 'completed')  # Update the expected status based on the initial DB setup


    def test_get_order_status_not_found(self):
        response = requests.get('http://127.0.0.1:5000/order/9999')  # Assuming this ID doesn't exist
        self.assertEqual(response.status_code, 404)
        error_message = response.json().get('error')
        self.assertEqual(error_message, 'Order not found')

    @patch('requests.get', side_effect=mock_driver_response)
    def test_update_order_status_success(self, mock_get):
        payload = {'items': 'Pizza'}
        create_response = requests.post('http://127.0.0.1:5000/order', json=payload)
        order_id = create_response.json()['order_id']

        update_payload = {'status': 'preparing'}
        response = requests.patch(f'http://127.0.0.1:5000/order/{order_id}', json=update_payload)
        self.assertEqual(response.status_code, 200)
        updated_data = response.json()
        self.assertEqual(updated_data['order_id'], order_id)
        self.assertEqual(updated_data['new_status'], 'preparing')

    def test_update_order_status_invalid_status(self):
        payload = {'items': 'Pizza'}
        create_response = requests.post('http://127.0.0.1:5000/order', json=payload)
        order_id = create_response.json()['order_id']

        update_payload = {'status': 'invalid_status'}
        response = requests.patch(f'http://127.0.0.1:5000/order/{order_id}', json=update_payload)
        self.assertEqual(response.status_code, 400)
        error_message = response.json().get('error')
        self.assertEqual(error_message, 'Invalid status')

    def test_update_order_status_order_not_found(self):
        update_payload = {'status': 'preparing'}
        response = requests.patch('http://127.0.0.1:5000/order/9999', json=update_payload)  # Assuming this ID doesn't exist
        self.assertEqual(response.status_code, 404)
        error_message = response.json().get('error')
        self.assertEqual(error_message, 'Order not found')

    def test_create_order_no_driver_available(self):

        with patch('requests.get') as mock_get:
            # Mock driver availability for this get request only
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'driver_status': 'unavailable'}
            payload = {'items': 'Burger, Fries'}
            response = requests.post('http://127.0.0.1:5000/order', json=payload) # Calls driver status
            time.sleep(3)
            self.assertEqual(response.status_code, 201)
            order_data = response.json()
            order_id = order_data['order_id']
        

        # Check that the order has been cancelled
        response = requests.get(f'http://127.0.0.1:5000/order/{order_id}')
        self.assertEqual(response.status_code, 404)
        error_message = response.json().get('error')
        self.assertEqual(error_message, 'Order not found')

    @classmethod
    def tearDownClass(cls):
        # Terminate threads if needed
        pass


if __name__ == '__main__':
    unittest.main()
