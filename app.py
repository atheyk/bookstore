from flask import Flask, request, jsonify, send_file
import sqlite3

# Adding comment to force Render redeployment - ignore
app = Flask(__name__)
DB_PATH = "bookstore.db"

# Home route to confirm API is working
@app.route('/')
def home():
    return "Bookstore API Connection Successful", 200

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
    data = request.json
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

        conn.commit()
        return jsonify({"message": "Order placed successfully"}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

# Record the transaction
@app.route('/record_sale', methods=['POST'])
def record_sale():
    data = request.json
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

# Adding a database download endpoint for the API here.. I went to work on the manufacturer sales and the inventory table was missing. Using this to download the last good file from Render - You guys can also use it to download the most up to date db file if you need it (Instead of having to go to GIT)

@app.route('/download-db', methods=['GET'])
def download_db():
    try:
        return send_file(DB_PATH, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
