from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://bookstore-website-mxovknmqp-shakirrasykes-projects.vercel.app"}})

DB_PATH = "bookstore.db"
UPLOAD_FOLDER = 'C:/Users/keena/OneDrive/Documents/Colorado Technical University/CS492/Bookstore/Images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return "Bookstore API Connection Successful", 200

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/upload-cover', methods=['POST'])
def upload_cover():
    if 'file' not in request.files or 'book_id' not in request.form:
        return jsonify({'error': 'File and book_id are required'}), 400

    file = request.files['file']
    book_id = request.form['book_id']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_extension = file.filename.rsplit('.', 1)[-1].lower()
    filename = f"book_{book_id}_{secure_filename(file.filename.rsplit('.', 1)[0])}.{file_extension}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    relative_path = f'static/uploads/{filename}'
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE books SET cover_image_path = ? WHERE id = ?", (relative_path, book_id))
        conn.commit()
        return jsonify({'cover_image_path': relative_path})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/cover-image/<filename>')
def get_cover_image(filename):
    filename = secure_filename(filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(image_path):
        return jsonify({"error": "Image not found"}), 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/inventory', methods=['GET'])
def get_inventory():
    conn = get_db_connection()
    books = conn.execute("SELECT id, book_title, stock_quantity, cover_image_path FROM books").fetchall()
    conn.close()

    inventory = []
    for book in books:
        book_dict = dict(book)
        if book_dict['cover_image_path'] and os.path.isfile(book_dict['cover_image_path']):
            book_dict['cover_image_url'] = request.host_url + 'cover-image/' + os.path.basename(book_dict['cover_image_path'])
        else:
            book_dict['cover_image_url'] = None

        inventory.append(book_dict)

    return jsonify(inventory)

@app.route('/check_stock/<int:book_id>', methods=['GET'])
def check_stock(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT stock_quantity FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()

    if book:
        return jsonify({"book_id": book_id, "stock_quantity": book["stock_quantity"]})
    else:
        return jsonify({"error": "Book not found"}), 404

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    customer_id, book_id, quantity = data["customer_id"], data["book_id"], data["quantity"]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        cursor.execute("SELECT stock_quantity FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()

        if not book or book["stock_quantity"] < quantity:
            return jsonify({"error": "Insufficient stock"}), 400

        cursor.execute("UPDATE books SET stock_quantity = stock_quantity - ? WHERE id = ?", (quantity, book_id))

        cursor.execute("INSERT INTO customer_orders (customer_id, book_id, quantity) VALUES (?, ?, ?)",
                       (customer_id, book_id, quantity))

        conn.commit()
        return jsonify({"message": "Order placed successfully"}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/record_sale', methods=['POST'])
def record_sale():
    data = request.json
    order_id, book_id, quantity, total_price = data["order_id"], data["book_id"], data["quantity"], data["total_price"]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute("INSERT INTO sales (order_id, book_id, quantity_sold, total_price) VALUES (?, ?, ?, ?)",
                       (order_id, book_id, quantity, total_price))

        conn.commit()
        return jsonify({"message": "Sale recorded successfully"}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/download-db', methods=['GET'])
def download_db():
    try:
        return send_file(DB_PATH, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
