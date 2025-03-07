import os
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = 'C:/Users/keena/OneDrive/Documents/Colorado Technical University/CS492/Bookstore/Images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        #Path to bookstore.db
        conn = sqlite3.connect('bookstore.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO books (title, image_path) VALUES (?, ?)", ('Book Title', filepath))
        conn.commit()
        conn.close()

        return f"File uploaded and stored in DB at {filepath}"
    return "Invalid file type"

if __name__ == '__main__':
    app.run(debug=True)
