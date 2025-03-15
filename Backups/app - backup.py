from flask import Flask, request, jsonify, send_file, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_PATH = "bookstore.db"
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Home route to confirm API is working
@app.route('/')
def home():
    return "Bookstore API Connection Successful", 200

# Database connection
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Image Upload Endpoint
@app.route('/upload-cover', methods=['POST'])
def upload_cover():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Return the file path for database storage
        return jsonify({'cover_image_path': file_path})

# Provide Book Cover Images
@app.route('/cover-image/<filename>')
def get_cover_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# View book inventory
@app.route('/inventory', methods=['GET'])
def get_inventory():
    conn = get_db_connection()
    books = conn.execute("SELECT id, book_title, stock_quantity, cover_image_path FROM books").fetchall()
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

# Feedback Submission Endpoint
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    book_id = data.get("book_id")
    rating = data.get("rating")
    comments = data.get("comments")

    if not book_id or not rating or not comments:
        return jsonify({"error": "All fields are required: book_id, rating, and comments"}), 400

    if not 1 <= int(rating) <= 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO UserFeedback (book_id, rating, comments, feedback_date)
            VALUES (?, ?, ?, DATE('now'))
        """, (book_id, rating, comments))

        conn.commit()
        return jsonify({"message": "Feedback submitted successfully!"}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

# Retrieve Feedback Endpoint (All Feedback or Specific Book)
@app.route('/feedback', methods=['GET'])
@app.route('/feedback/<int:book_id>', methods=['GET'])
def get_feedback(book_id=None):
    conn = get_db_connection()

    if book_id:
        feedback = conn.execute("SELECT * FROM UserFeedback WHERE book_id = ?", (book_id,)).fetchall()
    else:
        feedback = conn.execute("SELECT * FROM UserFeedback").fetchall()

    conn.close()

    if feedback:
        return jsonify([dict(entry) for entry in feedback])
    else:
        return jsonify({"message": "No feedback found."}), 404

# Database download endpoint
@app.route('/download-db', methods=['GET'])
def download_db():
    try:
        return send_file(DB_PATH, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
