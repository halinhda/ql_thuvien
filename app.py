# ============================================
# FILE: app.py - BACKEND FLASK + OOP (PostgreSQL) - PHIÊN BẢN ĐÃ SỬA LỖI URL
# ============================================

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import psycopg2 
from psycopg2 import errors
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-to-random-string-123456'

# ============================================
# PHẦN 1: CÁC CLASS OOP
# ============================================

class DatabaseManager:
    """Class quản lý database PostgreSQL"""
    
    # !!! THAY ĐỔI THÔNG SỐ KẾT NỐI CỦA BẠN TẠI ĐÂY !!!
    DB_NAME = "library_db"
    DB_USER = "admin"
    DB_PASSWORD = "1234" 
    DB_HOST = "localhost"
    DB_PORT = "5432"

    def __init__(self):
        self.init_database()

    def get_connection(self):
        """Tạo kết nối database PostgreSQL"""
        try:
            conn = psycopg2.connect(
                dbname=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT
            )
            return conn
        except psycopg2.Error as e:
            print(f"LỖI KẾT NỐI POSTGRESQL: {e}")
            raise ConnectionError(f"Không thể kết nối PostgreSQL. Lỗi: {e}")
    
    def init_database(self):
        """Khởi tạo các bảng trong database"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Bảng USERS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    email VARCHAR(100),
                    role VARCHAR(50) DEFAULT 'user',
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # Bảng BOOKS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    author VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    year INTEGER,
                    quantity INTEGER DEFAULT 1,
                    available INTEGER DEFAULT 1,
                    image_url TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # Bảng CART
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cart (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                    added_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE (user_id, book_id)
                )
            ''')
            
            # Bảng TRANSACTIONS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    book_id INTEGER NOT NULL REFERENCES books(id),
                    borrow_date TIMESTAMP DEFAULT NOW(),
                    due_date DATE NOT NULL,
                    return_date TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'borrowed',
                    points_earned INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            self.create_sample_data(cursor)
            
        except psycopg2.Error as e:
            print(f"LỖI KHỞI TẠO BẢNG: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def create_sample_data(self, cursor):
        """Tạo dữ liệu mẫu"""
        try:
            # Kiểm tra đã có user chưa
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO users (username, password, email, role, points)
                    VALUES 
                    ('admin', 'admin123', 'admin@library.com', 'admin', 0),
                    ('user1', 'user123', 'user1@example.com', 'user', 50)
                ''')
            
            # Kiểm tra đã có sách chưa
            cursor.execute("SELECT COUNT(*) FROM books")
            if cursor.fetchone()[0] == 0:
                books = [
                    ('Đắc Nhân Tâm', 'Dale Carnegie', 'Kỹ năng sống', 2020, 5, 5, 'https://salt.tikicdn.com/cache/750x750/ts/product/7e/14/a6/24a57c9536b51b41e3e9f8470cdf3ad3.jpg.webp', 'Sách về kỹ năng giao tiếp'),
                    ('Sapiens', 'Yuval Noah Harari', 'Lịch sử', 2018, 3, 3, 'https://salt.tikicdn.com/cache/750x750/ts/product/5e/18/24/2a6154ba08df6ce6161c13f4303fa19e.jpg.webp', 'Lịch sử loài người'),
                    ('Clean Code', 'Robert C. Martin', 'Công nghệ', 2019, 4, 4, 'https://m.media-amazon.com/images/I/51E2055ZGUL._SY445_SX342_.jpg', 'Viết code sạch'),
                    ('Hoàng Tử Bé', 'Antoine de Saint-Exupéry', 'Văn học', 2015, 6, 6, 'https://salt.tikicdn.com/cache/750x750/ts/product/45/3b/fc/aa81d0a534b45706b5559248a4f33ed3.jpg.webp', 'Truyện thiếu nhi'),
                    ('Nhà Giả Kim', 'Paulo Coelho', 'Văn học', 2017, 5, 5, 'https://salt.tikicdn.com/cache/750x750/ts/product/7a/85/d9/07e6c5758054c48ed9a47a09eba9c6f2.jpg.webp', 'Tiểu thuyết triết lý')
                ]
                
                cursor.executemany('''
                    INSERT INTO books (title, author, category, year, quantity, available, image_url, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', books)
            
            cursor.connection.commit()
        except Exception as e:
            print(f"Lỗi tạo dữ liệu mẫu: {e}")


class Person(ABC):
    """Class trừu tượng - ABSTRACTION"""
    
    def __init__(self, user_id, username, email, role, points=0):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.points = points
    
    @abstractmethod
    def get_permissions(self):
        pass
    
    def get_info(self):
        return {
            'id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'points': self.points
        }


class User(Person):
    """Người dùng - INHERITANCE & POLYMORPHISM"""
    
    def __init__(self, user_id, username, email, points=0):
        super().__init__(user_id, username, email, 'user', points)
        self.db = DatabaseManager()
    
    def get_permissions(self):
        return ['browse_books', 'borrow_books', 'return_books']
    
    def add_to_cart(self, book_id):
        """ENCAPSULATION - Đóng gói logic thêm giỏ"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT available FROM books WHERE id = %s", (book_id,))
            result = cursor.fetchone()
            
            if not result or result[0] <= 0:
                return False, "Sách không có sẵn!"
            
            cursor.execute('''
                SELECT * FROM cart WHERE user_id = %s AND book_id = %s
            ''', (self.user_id, book_id))
            
            if cursor.fetchone():
                return False, "Sách đã có trong giỏ!"
            
            cursor.execute('''
                INSERT INTO cart (user_id, book_id) VALUES (%s, %s)
            ''', (self.user_id, book_id))
            
            conn.commit()
            return True, "Đã thêm vào giỏ!"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()
    
    def get_cart(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, b.id, b.title, b.author, b.category, b.image_url
            FROM cart c
            JOIN books b ON c.book_id = b.id
            WHERE c.user_id = %s
        ''', (self.user_id,))
        
        cart_items = cursor.fetchall()
        conn.close()
        return cart_items
    
    def checkout(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT book_id FROM cart WHERE user_id = %s", (self.user_id,))
            book_ids = [row[0] for row in cursor.fetchall()]
            
            if not book_ids:
                return False, "Giỏ trống!"
            
            borrow_date = datetime.now()
            due_date = (borrow_date + timedelta(days=14)).date()
            
            for book_id in book_ids:
                cursor.execute('''
                    INSERT INTO transactions (user_id, book_id, due_date)
                    VALUES (%s, %s, %s)
                ''', (self.user_id, book_id, due_date))
                
                cursor.execute('''
                    UPDATE books SET available = available - 1 WHERE id = %s
                ''', (book_id,))
            
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (self.user_id,))
            
            conn.commit()
            return True, f"Đã mượn {len(book_ids)} cuốn sách!"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()
    
    def get_borrowed_books(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.id, b.title, b.author, t.borrow_date, t.due_date, b.image_url
            FROM transactions t
            JOIN books b ON t.book_id = b.id
            WHERE t.user_id = %s AND t.status = 'borrowed'
        ''', (self.user_id,))
        
        borrowed = cursor.fetchall()
        conn.close()
        return borrowed
    
    def return_book(self, transaction_id):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT book_id, due_date FROM transactions
                WHERE id = %s AND user_id = %s AND status = 'borrowed'
            ''', (transaction_id, self.user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, "Không tìm thấy giao dịch!"
            
            book_id, due_date = result
            return_date = datetime.now()
            points = 20 if return_date.date() <= due_date else 5
            
            cursor.execute('''
                UPDATE transactions
                SET status = 'returned', return_date = %s, points_earned = %s
                WHERE id = %s
            ''', (return_date, points, transaction_id))
            
            cursor.execute("UPDATE books SET available = available + 1 WHERE id = %s", (book_id,))
            cursor.execute("UPDATE users SET points = points + %s WHERE id = %s", (points, self.user_id))
            
            self.points += points
            
            conn.commit()
            return True, f"Đã trả sách! +{points} điểm"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()


class Admin(Person):
    """Quản trị viên - INHERITANCE & POLYMORPHISM"""
    
    def __init__(self, user_id, username, email, points=0):
        super().__init__(user_id, username, email, 'admin', points)
        self.db = DatabaseManager()
    
    def get_permissions(self):
        return ['all']
    
    def add_book(self, title, author, category, year, quantity, image_url='', description=''):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO books (title, author, category, year, quantity, available, image_url, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (title, author, category, year, quantity, quantity, image_url, description))
            
            conn.commit()
            return True, "Đã thêm sách mới!"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()
    
    def delete_book(self, book_id):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM transactions
                WHERE book_id = %s AND status = 'borrowed'
            ''', (book_id,))
            
            if cursor.fetchone()[0] > 0:
                return False, "Không thể xóa sách đang được mượn!"
            
            cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
            conn.commit()
            return True, "Đã xóa sách!"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()
    
    def get_statistics(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(available), 0) FROM books")
        result = cursor.fetchone()
        stats['total_books'] = result[0]
        stats['total_copies'] = result[1]
        stats['available_copies'] = result[2]
        stats['borrowed_copies'] = stats['total_copies'] - stats['available_copies']
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
        stats['total_users'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'borrowed'")
        stats['active_borrows'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def get_all_transactions(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.username, b.title, t.borrow_date, t.due_date, t.return_date, t.status
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN books b ON t.book_id = b.id
            ORDER BY t.borrow_date DESC
            LIMIT 50
        ''')
        
        transactions = cursor.fetchall()
        conn.close()
        return transactions

    def get_book_by_id(self, book_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, category, year, quantity, available, image_url, description
            FROM books
            WHERE id = %s
        ''', (book_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'category': row[3],
                'year': row[4],
                'quantity': row[5],
                'available': row[6],
                'image_url': row[7],
                'description': row[8]
            }
        return None

class LibrarySystem:
    """Hệ thống thư viện"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def register(self, username, password, email):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, password, email, role, points)
                VALUES (%s, %s, %s, 'user', 0)
            ''', (username, password, email))
            
            conn.commit()
            return True, "Đăng ký thành công!"
        except errors.UniqueViolation:
            if conn:
                conn.rollback()
            return False, "Username đã tồn tại!"
        except Exception as e:
            if conn:
                conn.rollback()
            return False, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()
    
    def login(self, username, password):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, role, points
                FROM users
                WHERE username = %s AND password = %s
            ''', (username, password))
            
            result = cursor.fetchone()
            
            if result:
                user_dict = {
                    'id': result[0],
                    'username': result[1],
                    'email': result[2],
                    'role': result[3],
                    'points': result[4]
                }
                return user_dict, "Đăng nhập thành công!"
            else:
                return None, "Sai username hoặc password!"
        except Exception as e:
            return None, f"Lỗi: {e}"
        finally:
            if conn:
                conn.close()
    
    def get_all_books(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, category, year, quantity, available, image_url, description
            FROM books
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        books = []
        for row in rows:
            books.append({
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'category': row[3],
                'year': row[4],
                'quantity': row[5],
                'available': row[6],
                'image_url': row[7],
                'description': row[8]
            })
        return books
        
    def get_book_by_id(self, book_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, category, year, quantity, available, image_url, description
            FROM books
            WHERE id = %s
        ''', (book_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'category': row[3],
                'year': row[4],
                'quantity': row[5],
                'available': row[6],
                'image_url': row[7],
                'description': row[8]
            }
        return None


# ============================================
# PHẦN 2: FLASK ROUTES
# ============================================

try:
    library_system = LibrarySystem()
except ConnectionError as e:
    print(f"\nLỖI: {e}\n")
    exit(1)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Vui lòng đăng nhập!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            flash('Bạn không có quyền truy cập!', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user' in session:
        if session['user']['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    books = library_system.get_all_books()
    return render_template('index.html', books=books)

# THÊM ROUTE NÀY ĐỂ KHẮC PHỤC LỖI BuildError
@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = library_system.get_book_by_id(book_id)
    if not book:
        flash('Không tìm thấy sách!', 'error')
        return redirect(url_for('index'))

    # Dùng render_template để hiển thị trang chi tiết
    return render_template('book_detail.html', book=book)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()
        
        if not username or not password or not email:
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return render_template('register.html')
        
        success, message = library_system.register(username, password, email)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Vui lòng nhập username và password!', 'error')
            return render_template('login.html')
        
        user_data, message = library_system.login(username, password)
        
        if user_data:
            session['user'] = user_data
            flash(message, 'success')
            
            if user_data['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash(message, 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Đã đăng xuất!', 'success')
    return redirect(url_for('index'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points']) 
    
    cart = user_obj.get_cart()
    borrowed = user_obj.get_borrowed_books()
    books = library_system.get_all_books()
    
    return render_template('user_dashboard.html', 
                           cart=cart, 
                           borrowed=borrowed,
                           books=books,
                           user=user_info)

@app.route('/user/add-to-cart/<int:book_id>')
@login_required
def add_to_cart(book_id):
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points']) 
    
    success, message = user_obj.add_to_cart(book_id)
    flash(message, 'success' if success else 'error')
    
    # Kiểm tra xem user có phải admin không (trường hợp admin xem trang index)
    if user_info['role'] == 'admin':
         return redirect(url_for('admin_dashboard'))
         
    return redirect(url_for('user_dashboard'))

@app.route('/user/checkout')
@login_required
def checkout():
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points']) 
    
    success, message = user_obj.checkout()
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('user_dashboard'))

@app.route('/user/return/<int:transaction_id>')
@login_required
def return_book(transaction_id):
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    success, message = user_obj.return_book(transaction_id)
    
    if success:
        # Cập nhật points trong session sau khi trả sách
        session['user']['points'] = user_obj.points
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('user_dashboard'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    admin_obj = Admin(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    stats = admin_obj.get_statistics()
    books = library_system.get_all_books()
    transactions = admin_obj.get_all_transactions()
    
    return render_template('admin_dashboard.html',
                           stats=stats,
                           books=books,
                           transactions=transactions,
                           user=user_info)

@app.route('/admin/add-book', methods=['POST'])
@admin_required
def admin_add_book():
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    admin_obj = Admin(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    category = request.form.get('category', '').strip()
    year = int(request.form.get('year', 2024))
    quantity = int(request.form.get('quantity', 1))
    image_url = request.form.get('image_url', '').strip()
    description = request.form.get('description', '').strip()
    
    if not title or not author or not category or quantity <= 0:
        flash('Vui lòng nhập đầy đủ Title, Author, Category và Quantity > 0.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    success, message = admin_obj.add_book(title, author, category, year, quantity, image_url, description)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-book/<int:book_id>')
@admin_required
def admin_delete_book(book_id):
    user_info = session['user']
    # ĐÃ SỬA: Đảm bảo truyền points
    admin_obj = Admin(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    success, message = admin_obj.delete_book(book_id)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('admin_dashboard'))

# Chức năng số lượng sách
@app.route('/admin/add_stock/<int:book_id>', methods=['POST'])
# @admin_required # Bỏ comment nếu bạn muốn yêu cầu quyền Admin
def admin_add_stock(book_id):
    conn = None 
    try:
        # 1. Lấy số lượng muốn thêm từ form (input name="quantity_added")
        quantity_to_add = int(request.form.get('quantity_added', 0))
    except ValueError:
        flash('Lỗi: Số lượng thêm vào phải là số nguyên hợp lệ.', 'error')
        return redirect(url_for('admin_dashboard'))

    if quantity_to_add <= 0:
        flash('Vui lòng nhập số lượng lớn hơn 0.', 'error')
        return redirect(url_for('admin_dashboard'))

    try:
        # Kết nối database
        conn = library_system.db.get_connection()
        cursor = conn.cursor()
        
        # 2. LỆNH SQL CẬP NHẬT KHO SÁCH
        # Tăng cả TỔNG SỐ LƯỢNG (quantity) và SẴN CÓ (available)
        cursor.execute(
            """
            UPDATE books 
            SET quantity = quantity + %s, 
                available = available + %s
            WHERE id = %s;
            """, 
            (quantity_to_add, quantity_to_add, book_id)
        )
        conn.commit() # BẮT BUỘC: Lưu thay đổi
        
        # Lấy tên sách để thông báo
        cursor.execute("SELECT title FROM books WHERE id = %s", (book_id,))
        book_title = cursor.fetchone()[0] if cursor.rowcount else f'ID: {book_id}'
        
        flash(f'Đã thêm {quantity_to_add} cuốn vào kho sách "{book_title}" thành công!', 'success')
        
    except Exception as e:
        if conn:
            conn.rollback() # Hoàn tác nếu có lỗi
        flash(f'Lỗi hệ thống hoặc database khi thêm số lượng: {e}', 'error')
        
    finally:
        if conn:
            cursor.close()
            conn.close() 

    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    print("="*60)
    print("  HỆ THỐNG THƯ VIỆN - FLASK + POSTGRESQL + OOP")
    print("="*60)
    print("\n✅ Server: http://127.0.0.1:5000")
    print("\n📌 Tài khoản mẫu:")
    print("   Admin: admin / admin123")
    print("   User:  user1 / user123")
    print("="*60)
    
    app.run(debug=True, port=5000)