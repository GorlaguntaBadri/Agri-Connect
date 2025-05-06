from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import mysql.connector
import os
from datetime import datetime
from main import db, app

# Create Flask app
app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/farmers'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))
    role = db.Column(db.String(20))

class Register(db.Model):
    rid = db.Column(db.Integer, primary_key=True)
    farmername = db.Column(db.String(50))
    adharnumber = db.Column(db.String(50))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(50))
    phonenumber = db.Column(db.String(50))
    address = db.Column(db.String(50))
    farming = db.Column(db.String(50))
    role = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)

class Addagroproducts(db.Model):
    pid = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(100))
    productdesc = db.Column(db.String(300))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float, nullable=True)
    is_validated = db.Column(db.Boolean, default=False)
    validator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    farmer_id = db.Column(db.Integer, db.ForeignKey('register.rid'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Run migration
if __name__ == "__main__":
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="farmers"
        )
        cursor = conn.cursor()
        
        # Check if user_id column exists in register table
        cursor.execute("SHOW COLUMNS FROM register LIKE 'user_id'")
        result = cursor.fetchone()
        
        if not result:
            # Add user_id column to register table
            cursor.execute("ALTER TABLE register ADD COLUMN user_id INT, ADD UNIQUE (user_id), ADD FOREIGN KEY (user_id) REFERENCES user(id)")
            print("user_id column added to register table successfully")
        else:
            print("user_id column already exists in register table")
        
        # Check if farmer_id column exists in addagroproducts table
        cursor.execute("SHOW COLUMNS FROM addagroproducts LIKE 'farmer_id'")
        result = cursor.fetchone()
        
        if not result:
            # Add farmer_id column to addagroproducts table
            cursor.execute("ALTER TABLE addagroproducts ADD COLUMN farmer_id INT, ADD FOREIGN KEY (farmer_id) REFERENCES register(rid)")
            print("farmer_id column added to addagroproducts table successfully")
        else:
            print("farmer_id column already exists in addagroproducts table")
            
        # Check if created_at column exists in addagroproducts table
        cursor.execute("SHOW COLUMNS FROM addagroproducts LIKE 'created_at'")
        result = cursor.fetchone()
        
        if not result:
            # Add created_at column to addagroproducts table
            cursor.execute("ALTER TABLE addagroproducts ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("created_at column added to addagroproducts table successfully")
        else:
            print("created_at column already exists in addagroproducts table")
            
        # Check if price column exists in addagroproducts table
        cursor.execute("SHOW COLUMNS FROM addagroproducts LIKE 'price'")
        result = cursor.fetchone()
        
        if not result:
            # Add price column to addagroproducts table
            cursor.execute("ALTER TABLE addagroproducts ADD COLUMN price FLOAT")
            print("price column added to addagroproducts table successfully")
        else:
            print("price column already exists in addagroproducts table")
            
        # Check if is_validated column exists in addagroproducts table
        cursor.execute("SHOW COLUMNS FROM addagroproducts LIKE 'is_validated'")
        result = cursor.fetchone()
        
        if not result:
            # Add is_validated column to addagroproducts table
            cursor.execute("ALTER TABLE addagroproducts ADD COLUMN is_validated BOOLEAN DEFAULT FALSE")
            print("is_validated column added to addagroproducts table successfully")
        else:
            print("is_validated column already exists in addagroproducts table")
            
        # Check if validator_id column exists in addagroproducts table
        cursor.execute("SHOW COLUMNS FROM addagroproducts LIKE 'validator_id'")
        result = cursor.fetchone()
        
        if not result:
            # Add validator_id column to addagroproducts table
            cursor.execute("ALTER TABLE addagroproducts ADD COLUMN validator_id INT, ADD FOREIGN KEY (validator_id) REFERENCES user(id)")
            print("validator_id column added to addagroproducts table successfully")
        else:
            print("validator_id column already exists in addagroproducts table")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

# Create cart table if it doesn't exist
try:
    with app.app_context():
        # Check if cart table exists
        result = db.session.execute("SHOW TABLES LIKE 'cart'")
        if not result.fetchone():
            # Create cart table
            db.session.execute("""
                CREATE TABLE cart (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id),
                    FOREIGN KEY (product_id) REFERENCES addagroproducts(pid)
                )
            """)
            db.session.commit()
            print("Cart table created successfully")
        else:
            print("Cart table already exists")
except Exception as e:
    print(f"Error creating cart table: {str(e)}")

# Create order table if it doesn't exist
try:
    with app.app_context():
        # Check if order table exists
        result = db.session.execute("SHOW TABLES LIKE 'order'")
        if not result.fetchone():
            # Create order table
            db.session.execute("""
                CREATE TABLE `order` (
                    order_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    total_amount FLOAT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            """)
            db.session.commit()
            print("Order table created successfully")
        else:
            print("Order table already exists")
except Exception as e:
    print(f"Error creating order table: {str(e)}")

# Create order_item table if it doesn't exist
try:
    with app.app_context():
        # Check if order_item table exists
        result = db.session.execute("SHOW TABLES LIKE 'order_item'")
        if not result.fetchone():
            # Create order_item table
            db.session.execute("""
                CREATE TABLE order_item (
                    item_id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL,
                    price FLOAT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES `order`(order_id),
                    FOREIGN KEY (product_id) REFERENCES addagroproducts(pid)
                )
            """)
            db.session.commit()
            print("Order item table created successfully")
        else:
            print("Order item table already exists")
except Exception as e:
    print(f"Error creating order item table: {str(e)}")

# Drop all tables
db.drop_all()

# Create all tables
db.create_all()

print("Database tables recreated successfully!") 