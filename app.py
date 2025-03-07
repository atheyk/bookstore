from flask import Flask, request, jsonify
import sqlite3


# Adding comment to force Render redeployment - ignore
app = Flask(__name__)
DB_PATH = "bookstore.db"

# Database connection
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# View book inventory
@app.route('/inventory', methods=['GET'])
def get_inventory():
    conn = get_db_connection()
    books = conn.execute("SELECT id, book_title, stock_quantity FROM books").fetchall()
    conn.close()
    return jsonify([dict(book) for book in books])

# Check stock prior to transaction
@app.route('/check_stock/<int:book_id>', methods=['GET'])
def check_stock(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT stock_quantity FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    if book:
        return jsonify({"book_id": book_id, "stock_quantity": book["stock_quantity"]})
    else:
        return jsonify({"error": "Book not found"}), 404

# Start Transaction
@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json  # Expected: { "customer_id": 1, "book_id": 2, "quantity": 1 }
    customer_id, book_id, quantity = data["customer_id"], data["book_id"], data["quantity"]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Check Stock
        cursor.execute("SELECT stock_quantity FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()
        
        if not book or book["stock_quantity"] < quantity:
            return jsonify({"error": "Insufficient stock"}), 400
        
        # Deduct Stock
        cursor.execute("UPDATE books SET stock_quantity = stock_quantity - ? WHERE id = ?", (quantity, book_id))
        
        # Insert Order
        cursor.execute("INSERT INTO customer_orders (customer_id, book_id, quantity) VALUES (?, ?, ?)", 
                       (customer_id, book_id, quantity))
        
        conn.commit()  # COMMIT if transaction is successful
        return jsonify({"message": "Order placed successfully"}), 201
    
    except Exception as e:
        conn.rollback()  # ROLLBACK if transaction failed
        return jsonify({"error": str(e)}), 500
    
    finally:
        conn.close()

# Record the transaction
@app.route('/record_sale', methods=['POST'])
def record_sale():
    data = request.json  # Expected: { "order_id": 1, "book_id": 2, "quantity": 1, "total_price": 19.99 }
    order_id, book_id, quantity, total_price = data["order_id"], data["book_id"], data["quantity"], data["total_price"]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Insert the sales record
        cursor.execute("INSERT INTO sales (order_id, book_id, quantity_sold, total_price) VALUES (?, ?, ?, ?)", 
                       (order_id, book_id, quantity, total_price))
        
        conn.commit()
        return jsonify({"message": "Sale recorded successfully"}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
