# Restaurant API

## Overview
This project simulates a restaurant system interacting with an Uber Eats API to handle menu items, order creation, and order tracking. It consists of three main components:
- **Restaurant API (`restaurant_api.py`)**: Manages menu items, orders, and communicates with the Uber Eats API.
- **Uber Eats API (`ubereats_api.py`)**: Simulates driver availability and updates order statuses.
- **Tests (`tests.py`)**: Contains unit tests to validate the functionality of the Restaurant API.

## Setup Instructions

### Prerequisites
- Python 3.x
- `pip` (Python package installer)

### Installation

#### 1. Clone the Repository
```sh
git clone <repository-url>
```

#### 2. Navigate to the Project Directory
```sh
cd RestaurantSideServer
```

#### 3. Create and Activate a Virtual Environment
It is recommended to use a virtual environment to manage dependencies.

On Windows:
```sh
python -m venv venv
venv\Scripts\activate
```

On macOS/Linux:
```sh
python3 -m venv venv
source venv/bin/activate
```

#### 4. Install Dependencies
```sh
pip install -r requirements.txt
```

#### 5. Initialize the Database
Run the following command to initialize the SQLite database with sample data:
```sh
python restaurant_db.py init_db
```

#### 6. Run the Servers

- **Restaurant API**:
  ```sh
  python restaurant_api.py run
  ```
  This will start the restaurant API on `http://127.0.0.1:5000`.

- **Uber Eats API**:
  ```sh
  python ubereats_api.py
  ```
  This will start the Uber Eats API on `http://127.0.0.1:5001`.

## Endpoints

### Restaurant API

#### 1. Create Order
- **URL**: `/order`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "items": "Burger, Fries"
  }
  ```
- **Response**:
  ```json
  {
    "order_id": 1,
    "status": "received",
    "timestamp": "2024-11-06T12:00:00"
  }
  ```
- **Description**: Creates a new order with the specified items.

#### 2. Get Order by ID
- **URL**: `/order/<int:order_id>`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "order_id": 1,
    "items": "Burger, Fries",
    "status": "received",
    "timestamp": "2024-11-06T12:00:00"
  }
  ```
- **Description**: Retrieves the order details for the specified `order_id`.

#### 3. Update Order Status
- **URL**: `/order/<int:order_id>`
- **Method**: `PATCH`
- **Request Body**:
  ```json
  {
    "status": "preparing"
  }
  ```
- **Response**:
  ```json
  {
    "order_id": 1,
    "new_status": "preparing"
  }
  ```
- **Description**: Updates the status of the specified order.

### Uber Eats API

#### 1. Get Driver Status
- **URL**: `/uber/driver_status`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "driver_status": "available"
  }
  ```
- **Description**: Returns whether a driver is available.

#### 2. Update Order Status
- **URL**: `/uber/order/<int:order_id>`
- **Method**: `PATCH`
- **Request Body**:
  ```json
  {
    "status": "completed"
  }
  ```
- **Response**:
  ```json
  {
    "order_id": 1,
    "new_status": "completed"
  }
  ```
- **Description**: Updates the status of an order in the Uber Eats system.

## Running Tests
To run the unit tests, use the following command:
```sh
python -m unittest tests.py
```

This will execute all the test cases to ensure the functionality of the API is working as expected.

