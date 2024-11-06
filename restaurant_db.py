import sqlite3
from datetime import datetime
import sys

def init_db():

    print("Initializing database.")

    with sqlite3.connect('restaurant.db') as conn:
        c = conn.cursor()
        # Drop existing tables if they exist
        c.execute('DROP TABLE IF EXISTS menu')
        c.execute('DROP TABLE IF EXISTS orders')
        # Menu schema
        c.execute('''CREATE TABLE IF NOT EXISTS menu (
                     id INTEGER PRIMARY KEY,
                     name TEXT NOT NULL,
                     price REAL NOT NULL,
                     available BOOLEAN NOT NULL DEFAULT 1)''')
        # Orders schema
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     items TEXT NOT NULL,
                     status TEXT NOT NULL,
                     timestamp TEXT NOT NULL)''')
        
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

        orders = [
            (1, 'Burger, Fries', 'completed', datetime.now().isoformat()),
            (2, 'Pizza', 'preparing', datetime.now().isoformat()),
            (3, 'Chicken Wings, Soda', 'received', datetime.now().isoformat()),
            (4, 'Pasta', 'ready', datetime.now().isoformat())
        ]
        c.executemany('INSERT OR IGNORE INTO orders (id, items, status, timestamp) VALUES (?, ?, ?, ?)', orders)
        conn.commit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'init_db':
            init_db()
        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        print("No command provided.")