# ============================================
# FILE: app.py - BACKEND FLASK + OOP (PostgreSQL) - PHIÊN BẢN ĐÃ SỬA LỖI URL
# ============================================

# IMPORT CÁC THƯ VIỆN CẦN THIẾT
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
DATABASE_URL = os.environ.get('DATABASE_URL')  # Lấy URL database từ biến môi trường (dùng khi deploy)
import psycopg2  # Thư viện kết nối PostgreSQL
import psycopg2.extras  # Thư viện hỗ trợ thao tác nâng cao với PostgreSQL
from psycopg2 import errors  # Import các lỗi của PostgreSQL
from datetime import datetime, timedelta  # Xử lý ngày tháng
from abc import ABC, abstractmethod  # Tạo class trừu tượng (Abstract Base Class)
from functools import wraps  # Dùng để tạo decorator
import os
from dotenv import load_dotenv 

# KHỞI TẠO ỨNG DỤNG FLASK
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_fallback_key')  # Khóa bí mật cho session

# ============================================
# PHẦN 1: CÁC CLASS OOP
# ============================================

class DatabaseManager:
    """
    QUẢN LÝ DATABASE (LOCAL + RENDER)
    - Nếu local PostgreSQL đang chạy → dùng local (bản demo cá nhân)
    - Nếu local không mở → fallback sang Render database
    """

    LOCAL_DB_CONFIG = {
        'dbname': "library_db",
        'user': "admin",     # hoặc user bạn tạo
        'password': "1234",
        'host': "localhost",
        'port': "5432"
    }

    def __init__(self):
        load_dotenv()  # đọc DATABASE_URL từ .env
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        print("🚀 Khởi tạo DatabaseManager...")
        self.active_db = None
        self.init_database()

    def get_connection(self):
        """
        ƯU TIÊN LOCAL → nếu lỗi → Render
        """
        # Thử Local trước
        try:
            conn = psycopg2.connect(**self.LOCAL_DB_CONFIG)
            self.active_db = "local"
            print("💻 Đang sử dụng database LOCAL (demo cá nhân).")
            return conn
        except Exception as e:
            print("⚠️ Local DB không khả dụng:", e)

        # Nếu Local lỗi → thử Render
        try:
            if not self.DATABASE_URL:
                raise Exception("Không có DATABASE_URL trong .env!")
            conn = psycopg2.connect(self.DATABASE_URL, sslmode='require')
            self.active_db = "render"
            print("🌐 Kết nối tới Render PostgreSQL thành công!")
            return conn
        except Exception as e:
            print("❌ Không thể kết nối tới Render DB:", e)
            raise RuntimeError("Không thể kết nối tới cả Local và Render Database!")

    def init_database(self):
        """
        KHỞI TẠO DATABASE: Tạo các bảng và dữ liệu mẫu nếu chưa có
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # --- TẠO BẢNG USERS (Người dùng) ---
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,                 -- ID tự động tăng
                    username VARCHAR(100) UNIQUE NOT NULL, -- Tên đăng nhập (duy nhất)
                    password VARCHAR(100) NOT NULL,        -- Mật khẩu
                    email VARCHAR(100),                    -- Email
                    role VARCHAR(50) DEFAULT 'user',       -- Vai trò: 'user' hoặc 'admin'
                    points INTEGER DEFAULT 0,              -- Điểm tích lũy
                    created_at TIMESTAMP DEFAULT NOW()     -- Ngày tạo tài khoản
                )
            ''')
            
            # --- TẠO BẢNG BOOKS (Sách) ---
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,              -- ID sách
                    title VARCHAR(255) NOT NULL,        -- Tên sách
                    author VARCHAR(255) NOT NULL,       -- Tác giả
                    category VARCHAR(100) NOT NULL,     -- Thể loại
                    year INTEGER,                       -- Năm xuất bản
                    quantity INTEGER DEFAULT 1,         -- Tổng số lượng
                    available INTEGER DEFAULT 1,        -- Số lượng có sẵn để mượn
                    image_url TEXT,                     -- Link ảnh bìa
                    description TEXT,                   -- Mô tả sách
                    created_at TIMESTAMP DEFAULT NOW()  -- Ngày thêm sách
                )
            ''')

            # --- CHÈN DỮ LIỆU MẪU NẾU BẢNG TRỐNG ---
            # Kiểm tra xem bảng users có dữ liệu chưa
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                # Thêm tài khoản mẫu: 1 admin và 1 user
                cursor.execute('''
                    INSERT INTO users (username, password, email, role, points)
                    VALUES 
                    ('admin', 'admin123', 'admin@library.com', 'admin', 0),
                    ('user1', 'user123', 'user1@example.com', 'user', 50)
                ''')

            # Kiểm tra xem bảng books có dữ liệu chưa
            cursor.execute("SELECT COUNT(*) FROM books")
            if cursor.fetchone()[0] == 0:
                # Thêm sách mẫu
                books = [
                    ('Đắc Nhân Tâm', 'Dale Carnegie', 'Kỹ năng sống', 2020, 5, 5, 'https://i.pinimg.com/1200x/1c/22/df/1c22df7132ad8f1358688b23831e9eaf.jpg', 'Sách về kỹ năng giao tiếp'),
                    ('Sapiens', 'Yuval Noah Harari', 'Lịch sử', 2018, 3, 3, 'https://i.pinimg.com/1200x/ef/68/e5/ef68e5753d6bd53fbc099c9003ad1abb.jpg', 'Lịch sử loài người'),
                ]
                cursor.executemany('''
                    INSERT INTO books (title, author, category, year, quantity, available, image_url, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', books)

            conn.commit()  # Lưu tất cả thay đổi vào database
            cursor.close()
            conn.close()
            print("[INFO] Database đã được đồng bộ thành công!")

        except Exception as e:
            print(f"[ERROR] Đồng bộ database thất bại: {e}")
            if conn:
                conn.rollback()  # Hoàn tác nếu có lỗi
                conn.close()


    def init_database(self):
        """
        KHỞI TẠO CÁC BẢNG VÀ DỮ LIỆU MẪU
        - Tạo 4 bảng: users, books, cart, transactions
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # --- BẢNG USERS (Người dùng) ---
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

                    # --- BẢNG BOOKS (Sách) ---
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

                    # --- BẢNG CART (Giỏ sách - sách user định mượn) ---
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS cart (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- Khóa ngoại đến users
                            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,  -- Khóa ngoại đến books
                            added_at TIMESTAMP DEFAULT NOW(),                                 -- Thời gian thêm vào giỏ
                            UNIQUE (user_id, book_id)  -- 1 user không thể thêm 1 sách 2 lần
                        )
                    ''')

                    # --- BẢNG TRANSACTIONS (Lịch sử mượn trả) ---
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS transactions (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id),      -- User nào mượn
                            book_id INTEGER NOT NULL REFERENCES books(id),      -- Sách nào
                            borrow_date TIMESTAMP DEFAULT NOW(),                -- Ngày mượn
                            due_date DATE NOT NULL,                             -- Ngày phải trả
                            return_date TIMESTAMP,                              -- Ngày trả thực tế (NULL nếu chưa trả)
                            status VARCHAR(50) DEFAULT 'borrowed',              -- Trạng thái: 'borrowed' hoặc 'returned'
                            points_earned INTEGER DEFAULT 0                     -- Điểm nhận được khi trả
                        )
                    ''')

                    # Lưu thay đổi sau khi tạo bảng
                    conn.commit()

                    # Tạo dữ liệu mẫu
                    self.create_sample_data(cursor, conn)

                    print("[INFO] Database và bảng đã sẵn sàng.")
        except psycopg2.Error as e:
            print(f"[ERROR] Khởi tạo database thất bại: {e}")

    def create_sample_data(self, cursor, conn):
        """
        TẠO DỮ LIỆU MẪU CHO BẢNG USERS VÀ BOOKS (nếu bảng trống)
        """
        try:
            # --- THÊM DỮ LIỆU CHO BẢNG USERS ---
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO users (username, password, email, role, points)
                    VALUES 
                    ('admin', 'admin123', 'admin@library.com', 'admin', 0),
                    ('user1', 'user123', 'user1@example.com', 'user', 50)
                ''')

            # --- THÊM DỮ LIỆU CHO BẢNG BOOKS ---
            cursor.execute("SELECT COUNT(*) FROM books")
            if cursor.fetchone()[0] == 0:
                books = [
                    ('Đắc Nhân Tâm', 'Dale Carnegie', 'Kỹ năng sống', 2020, 5, 5, 'https://i.pinimg.com/1200x/1c/22/df/1c22df7132ad8f1358688b23831e9eaf.jpg', 'Sách về kỹ năng giao tiếp'),
                    ('Sapiens', 'Yuval Noah Harari', 'Lịch sử', 2018, 3, 3, 'https://salt.tikicdn.com/cache/750x750/ts/product/5e/18/24/2a6154ba08df6ce6161c13f4303fa19e.jpg.webp', 'Lịch sử loài người'),
                    ('Clean Code', 'Robert C. Martin', 'Công nghệ', 2019, 4, 4, 'https://m.media-amazon.com/images/I/51E2055ZGUL._SY445_SX342_.jpg', 'Viết code sạch'),
                    ('Hoàng Tử Bé', 'Antoine de Saint-Exupéry', 'Văn học', 2015, 6, 6, 'https://i.pinimg.com/736x/73/fe/f2/73fef2d17b9f311e713bee4bcba584d7.jpg', 'Truyện thiếu nhi'),
                    ('Nhà Giả Kim', 'Paulo Coelho', 'Văn học', 2017, 5, 5, 'https://i.pinimg.com/736x/e7/9b/61/e79b615c3277569a59e312943707eeae.jpg', 'Tiểu thuyết triết lý')
                ]
                cursor.executemany('''
                    INSERT INTO books (title, author, category, year, quantity, available, image_url, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', books)

            conn.commit()
            print("[INFO] Sample data đã được thêm (nếu bảng rỗng).")

        except Exception as e:
            print(f"[ERROR] Tạo dữ liệu mẫu thất bại: {e}")



class Person(ABC):
    """
    CLASS TRỪU TƯỢNG (ABSTRACT CLASS) - ĐẠI DIỆN CHO MỘT NGƯỜI DÙNG
    - Đây là class cha, không thể tạo đối tượng trực tiếp
    - Các class con (User, Admin) phải kế thừa và implement method get_permissions()
    """
    
    def __init__(self, user_id, username, email, role, points=0):
        """KHỞI TẠO: Lưu thông tin cơ bản của người dùng"""
        self.user_id = user_id      # ID người dùng
        self.username = username    # Tên đăng nhập
        self.email = email          # Email
        self.role = role            # Vai trò: 'user' hoặc 'admin'
        self.points = points        # Điểm tích lũy
    
    @abstractmethod
    def get_permissions(self):
        """
        METHOD TRỪU TƯỢNG: Mỗi class con phải tự định nghĩa quyền hạn
        - User: chỉ được mượn/trả sách
        - Admin: toàn quyền
        """
        pass
    
    def get_info(self):
        """TRẢ VỀ THÔNG TIN CƠ BẢN CỦA NGƯỜI DÙNG dưới dạng dictionary"""
        return {
            'id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'points': self.points
        }


class User(Person):
    """
    CLASS USER (NGƯỜI DÙNG THÔNG THƯỜNG)
    - Kế thừa từ Person
    - Có quyền: xem sách, thêm vào giỏ, mượn, trả sách
    """
    
    def __init__(self, user_id, username, email, points=0):
        """KHỞI TẠO: Gọi constructor của class cha với role='user'"""
        super().__init__(user_id, username, email, 'user', points)
        self.db = DatabaseManager()  # Tạo kết nối database
    
    def get_permissions(self):
        """QUYỀN HẠN CỦA USER: chỉ được browse và borrow sách"""
        return ['browse_books', 'borrow_books', 'return_books']
    
    def add_to_cart(self, book_id):
        """
        THÊM SÁCH VÀO GIỎ
        - Kiểm tra sách còn available không
        - Kiểm tra sách đã có trong giỏ chưa
        - Thêm vào bảng cart
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Kiểm tra sách còn available không
            cursor.execute("SELECT available FROM books WHERE id = %s", (book_id,))
            result = cursor.fetchone()
            
            if not result or result[0] <= 0:
                return False, "Sách không có sẵn!"
            
            # Kiểm tra sách đã có trong giỏ chưa
            cursor.execute('''
                SELECT * FROM cart WHERE user_id = %s AND book_id = %s
            ''', (self.user_id, book_id))
            
            if cursor.fetchone():
                return False, "Sách đã có trong giỏ!"
            
            # Thêm sách vào giỏ
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
        """
        LẤY DANH SÁCH SÁCH TRONG GIỎ CỦA USER
        - JOIN bảng cart với bảng books để lấy thông tin sách
        """
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
        """
        THANH TOÁN GIỎ HÀNG (MƯỢN TẤT CẢ SÁCH TRONG GIỎ)
        - Lấy tất cả book_id trong giỏ
        - Tạo transaction cho từng sách (thời hạn 14 ngày)
        - Giảm available của sách
        - Xóa giỏ hàng
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Lấy tất cả sách trong giỏ
            cursor.execute("SELECT book_id FROM cart WHERE user_id = %s", (self.user_id,))
            book_ids = [row[0] for row in cursor.fetchall()]
            
            if not book_ids:
                return False, "Giỏ trống!"
            
            # Tính ngày mượn và ngày phải trả (14 ngày sau)
            borrow_date = datetime.now()
            due_date = (borrow_date + timedelta(days=14)).date()
            
            # Tạo transaction cho từng sách
            for book_id in book_ids:
                cursor.execute('''
                    INSERT INTO transactions (user_id, book_id, due_date)
                    VALUES (%s, %s, %s)
                ''', (self.user_id, book_id, due_date))
                
                # Giảm available của sách
                cursor.execute('''
                    UPDATE books SET available = available - 1 WHERE id = %s
                ''', (book_id,))
            
            # Xóa giỏ hàng sau khi mượn
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
        """
        LẤY DANH SÁCH SÁCH ĐANG MƯỢN CỦA USER
        - Chỉ lấy transaction có status = 'borrowed'
        """
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
        """
        TRẢ SÁCH
        - Kiểm tra transaction có tồn tại và thuộc user này không
        - Tính điểm: +20 nếu trả đúng hạn, +5 nếu trả trễ
        - Cập nhật status = 'returned', lưu return_date
        - Tăng available của sách
        - Cộng điểm cho user
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Lấy thông tin transaction
            cursor.execute('''
                SELECT book_id, due_date FROM transactions
                WHERE id = %s AND user_id = %s AND status = 'borrowed'
            ''', (transaction_id, self.user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, "Không tìm thấy giao dịch!"
            
            book_id, due_date = result
            return_date = datetime.now()
            
            # Tính điểm: đúng hạn +20, trễ hạn +5
            points = 20 if return_date.date() <= due_date else 5
            
            # Cập nhật transaction
            cursor.execute('''
                UPDATE transactions
                SET status = 'returned', return_date = %s, points_earned = %s
                WHERE id = %s
            ''', (return_date, points, transaction_id))
            
            # Tăng available của sách
            cursor.execute("UPDATE books SET available = available + 1 WHERE id = %s", (book_id,))
            
            # Cộng điểm cho user
            cursor.execute("UPDATE users SET points = points + %s WHERE id = %s", (points, self.user_id))
            
            # Cập nhật points trong object
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
    """
    CLASS ADMIN (QUẢN TRỊ VIÊN)
    - Kế thừa từ Person
    - Có toàn quyền: quản lý sách, xem thống kê, xem lịch sử
    """
    
    def __init__(self, user_id, username, email, points=0):
        """KHỞI TẠO: Gọi constructor của class cha với role='admin'"""
        super().__init__(user_id, username, email, 'admin', points)
        self.db = DatabaseManager()
    
    def get_permissions(self):
        """QUYỀN HẠN CỦA ADMIN: toàn quyền"""
        return ['all']
    
    def add_book(self, title, author, category, year, quantity, image_url='', description=''):
        """
        THÊM SÁCH MỚI VÀO HỆ THỐNG
        - available = quantity (sách mới thì tất cả đều available)
        """
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
        """
        XÓA SÁCH
        - Kiểm tra sách có đang được mượn không (status='borrowed')
        - Nếu không ai mượn thì mới được xóa
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Kiểm tra sách có đang được mượn không
            cursor.execute('''
                SELECT COUNT(*) FROM transactions
                WHERE book_id = %s AND status = 'borrowed'
            ''', (book_id,))
            
            if cursor.fetchone()[0] > 0:
                return False, "Không thể xóa sách đang được mượn!"
            
            # Xóa sách
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
        """
        LẤY THỐNG KÊ HỆ THỐNG
        - Tổng số đầu sách, tổng số bản, số bản available
        - Số user, số lượt mượn hiện tại
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Thống kê sách
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(available), 0) FROM books")
        result = cursor.fetchone()
        stats['total_books'] = result[0]        # Tổng số đầu sách
        stats['total_copies'] = result[1]       # Tổng số bản
        stats['available_copies'] = result[2]   # Số bản có sẵn
        stats['borrowed_copies'] = stats['total_copies'] - stats['available_copies']  # Số bản đang mượn
        
        # Thống kê user
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
        stats['total_users'] = cursor.fetchone()[0]
        
        # Số lượt mượn hiện tại
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'borrowed'")
        stats['active_borrows'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def get_all_transactions(self):
        """
        LẤY LỊCH SỬ MƯỢN TRẢ (50 GIAO DỊCH GẦN NHẤT)
        - JOIN 3 bảng: transactions, users, books
        - Sắp xếp theo thời gian mượn (mới nhất trước)
        """
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
        """
        LẤY THÔNG TIN CHI TIẾT MỘT CUỐN SÁCH
        - Dùng để hiển thị trang chi tiết hoặc form edit
        """
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
    """
    CLASS HỆ THỐNG THƯ VIỆN
    - Quản lý đăng ký, đăng nhập
    - Lấy danh sách sách
    """
    
    def __init__(self):
        """KHỞI TẠO: Tạo kết nối database"""
        self.db = DatabaseManager()
    
    def register(self, username, password, email):
        """
        ĐĂNG KÝ TÀI KHOẢN MỚI
        - Mặc định role = 'user', points = 0
        - Username phải unique (không trùng)
        """
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
            # Lỗi unique: username đã tồn tại
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
        """
        ĐĂNG NHẬP
        - Kiểm tra username và password
        - Trả về thông tin user nếu đúng
        """
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
                # Tạo dictionary chứa thông tin user
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
        """
        LẤY TẤT CẢ SÁCH TRONG HỆ THỐNG
        - Sắp xếp theo ngày thêm (mới nhất trước)
        - Trả về dạng list of dictionaries
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, category, year, quantity, available, image_url, description
            FROM books
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Chuyển đổi từng row thành dictionary
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
        """
        LẤY THÔNG TIN CHI TIẾT MỘT CUỐN SÁCH THEO ID
        """
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
# PHẦN 2: FLASK ROUTES (CÁC URL ENDPOINT)
# ============================================

# Khởi tạo hệ thống thư viện (kết nối database)
try:
    library_system = LibrarySystem()
except ConnectionError as e:
    print(f"\nLỖI: {e}\n")
    exit(1)

# ============================================
# DECORATOR: KIỂM TRA ĐĂNG NHẬP
# ============================================

def login_required(f):
    """
    DECORATOR: YÊU CẦU PHẢI ĐĂNG NHẬP
    - Dùng cho các route cần đăng nhập mới truy cập được
    - Nếu chưa đăng nhập -> chuyển về trang login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Vui lòng đăng nhập!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    DECORATOR: YÊU CẦU PHẢI LÀ ADMIN
    - Dùng cho các route chỉ admin mới truy cập được
    - Nếu không phải admin -> về trang chủ
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            flash('Bạn không có quyền truy cập!', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ROUTES: TRANG CHỦ VÀ XÁC THỰC
# ============================================

@app.route('/')
def index():
    """
    TRANG CHỦ
    - Nếu đã đăng nhập: chuyển đến dashboard tương ứng (user/admin)
    - Nếu chưa đăng nhập: hiển thị danh sách sách
    """
    if 'user' in session:
        if session['user']['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    books = library_system.get_all_books()
    return render_template('index.html', books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    """
    TRANG CHI TIẾT SÁCH
    - Hiển thị thông tin đầy đủ của 1 cuốn sách
    - Route này khắc phục lỗi BuildError khi click vào sách
    """
    book = library_system.get_book_by_id(book_id)
    if not book:
        flash('Không tìm thấy sách!', 'error')
        return redirect(url_for('index'))

    # Render trang chi tiết sách
    return render_template('book_detail.html', book=book)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    ĐĂNG KÝ TÀI KHOẢN
    - GET: Hiển thị form đăng ký
    - POST: Xử lý đăng ký
    """
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()
        
        # Kiểm tra dữ liệu có đầy đủ không
        if not username or not password or not email:
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return render_template('register.html')
        
        # Gọi hàm đăng ký từ LibrarySystem
        success, message = library_system.register(username, password, email)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))  # Chuyển đến trang login
        else:
            flash(message, 'error')
            return render_template('register.html')
    
    # GET request: hiển thị form
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    ĐĂNG NHẬP
    - GET: Hiển thị form đăng nhập
    - POST: Xử lý đăng nhập
    """
    if request.method == 'POST':
        # Lấy username và password từ form
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Vui lòng nhập username và password!', 'error')
            return render_template('login.html')
        
        # Gọi hàm login từ LibrarySystem
        user_data, message = library_system.login(username, password)
        
        if user_data:
            # Lưu thông tin user vào session (giống cookie)
            session['user'] = user_data
            flash(message, 'success')
            
            # Chuyển hướng dựa vào role
            if user_data['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash(message, 'error')
            return render_template('login.html')
    
    # GET request: hiển thị form
    return render_template('login.html')

@app.route('/logout')
def logout():
    """
    ĐĂNG XUẤT
    - Xóa session user
    - Chuyển về trang chủ
    """
    session.pop('user', None)
    flash('Đã đăng xuất!', 'success')
    return redirect(url_for('index'))

# ============================================
# ROUTES: DASHBOARD VÀ CHỨC NĂNG USER
# ============================================

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    """
    DASHBOARD CỦA USER
    - Hiển thị: giỏ hàng, sách đang mượn, danh sách sách
    """
    user_info = session['user']
    # Tạo object User để gọi các method
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points']) 
    
    cart = user_obj.get_cart()                  # Giỏ hàng
    borrowed = user_obj.get_borrowed_books()     # Sách đang mượn
    books = library_system.get_all_books()       # Tất cả sách
    
    return render_template('user_dashboard.html', 
                           cart=cart, 
                           borrowed=borrowed,
                           books=books,
                           user=user_info)

@app.route('/user/add-to-cart/<int:book_id>')
@login_required
def add_to_cart(book_id):
    """
    THÊM SÁCH VÀO GIỎ
    - Gọi method add_to_cart() của User
    """
    user_info = session['user']
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points']) 
    
    success, message = user_obj.add_to_cart(book_id)
    flash(message, 'success' if success else 'error')
    
    # Nếu user là admin thì về admin dashboard
    if user_info['role'] == 'admin':
         return redirect(url_for('admin_dashboard'))
         
    return redirect(url_for('user_dashboard'))

@app.route('/user/checkout')
@login_required
def checkout():
    """
    THANH TOÁN (MƯỢN SÁCH)
    - Mượn tất cả sách trong giỏ
    """
    user_info = session['user']
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points']) 
    
    success, message = user_obj.checkout()
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('user_dashboard'))

@app.route('/user/return/<int:transaction_id>')
@login_required
def return_book(transaction_id):
    """
    TRẢ SÁCH
    - Trả sách theo transaction_id
    - Cập nhật points trong session sau khi trả
    """
    user_info = session['user']
    user_obj = User(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    success, message = user_obj.return_book(transaction_id)
    
    if success:
        # Cập nhật points trong session
        session['user']['points'] = user_obj.points
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('user_dashboard'))

# ============================================
# ROUTES: DASHBOARD VÀ CHỨC NĂNG ADMIN
# ============================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """
    DASHBOARD CỦA ADMIN
    - Hiển thị: thống kê, danh sách sách, lịch sử giao dịch
    """
    user_info = session['user']
    # Tạo object Admin để gọi các method
    admin_obj = Admin(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    stats = admin_obj.get_statistics()          # Thống kê
    books = library_system.get_all_books()       # Danh sách sách
    transactions = admin_obj.get_all_transactions()  # Lịch sử
    
    return render_template('admin_dashboard.html',
                           stats=stats,
                           books=books,
                           transactions=transactions,
                           user=user_info)

@app.route('/admin/add-book', methods=['POST'])
@admin_required
def admin_add_book():
    """
    THÊM SÁCH MỚI (ADMIN)
    - Lấy dữ liệu từ form
    - Gọi method add_book() của Admin
    """
    user_info = session['user']
    admin_obj = Admin(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    # Lấy dữ liệu từ form
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    category = request.form.get('category', '').strip()
    year = int(request.form.get('year', 2024))
    quantity = int(request.form.get('quantity', 1))
    image_url = request.form.get('image_url', '').strip()
    description = request.form.get('description', '').strip()
    
    # Validate dữ liệu
    if not title or not author or not category or quantity <= 0:
        flash('Vui lòng nhập đầy đủ Title, Author, Category và Quantity > 0.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    success, message = admin_obj.add_book(title, author, category, year, quantity, image_url, description)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-book/<int:book_id>')
@admin_required
def admin_delete_book(book_id):
    """
    XÓA SÁCH (ADMIN)
    - Gọi method delete_book() của Admin
    """
    user_info = session['user']
    admin_obj = Admin(user_info['id'], user_info['username'], user_info['email'], user_info['points'])
    
    success, message = admin_obj.delete_book(book_id)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_stock/<int:book_id>', methods=['POST'])
# @admin_required  # Bỏ comment nếu muốn yêu cầu quyền Admin
def admin_add_stock(book_id):
    """
    THÊM SỐ LƯỢNG SÁCH VÀO KHO
    - Tăng cả quantity (tổng số) và available (có sẵn)
    - Dùng khi nhập thêm sách vào thư viện
    """
    conn = None 
    try:
        # 1. Lấy số lượng muốn thêm từ form (input name="quantity_added")
        quantity_to_add = int(request.form.get('quantity_added', 0))
    except ValueError:
        flash('Lỗi: Số lượng thêm vào phải là số nguyên hợp lệ.', 'error')
        return redirect(url_for('admin_dashboard'))

    # Kiểm tra số lượng phải > 0
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
        conn.commit()  # BẮT BUỘC: Lưu thay đổi vào database
        
        # Lấy tên sách để hiển thị thông báo
        cursor.execute("SELECT title FROM books WHERE id = %s", (book_id,))
        book_title = cursor.fetchone()[0] if cursor.rowcount else f'ID: {book_id}'
        
        flash(f'Đã thêm {quantity_to_add} cuốn vào kho sách "{book_title}" thành công!', 'success')
        
    except Exception as e:
        if conn:
            conn.rollback()  # Hoàn tác nếu có lỗi
        flash(f'Lỗi hệ thống hoặc database khi thêm số lượng: {e}', 'error')
        
    finally:
        # Đóng kết nối database
        if conn:
            cursor.close()
            conn.close() 

    return redirect(url_for('admin_dashboard'))

#===========================================
# TÌM KIẾM SÁCH
#===========================================
@app.route('/search', methods=['GET', 'POST'])
def search_books():
    query = ''
    results = []
    conn = None
    cursor = None  # ✅ đảm bảo biến này luôn tồn tại

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            flash('Vui lòng nhập từ khóa tìm kiếm!', 'error')
            return redirect(url_for('search_books'))

        try:
            # ✅ Kết nối database PostgreSQL
            conn = library_system.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # ✅ Tìm theo tên, tác giả, hoặc năm
            sql = """
                SELECT * FROM books
                WHERE title ILIKE %s
                OR author ILIKE %s
                OR CAST(year AS TEXT) ILIKE %s
                ORDER BY title ASC
            """
            values = (f'%{query}%', f'%{query}%', f'%{query}%')
            cursor.execute(sql, values)
            results = cursor.fetchall()

            if not results:
                flash(f'Không tìm thấy sách nào phù hợp với từ khóa "{query}"!', 'info')


        except Exception as e:
            flash(f'Lỗi khi tìm kiếm sách: {e}', 'error')

        finally:
            # ✅ Chỉ đóng nếu thực sự tồn tại
            if cursor is not None:
                try:
                    cursor.close()
                except:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except:
                    pass

    return render_template('search.html', query=query, results=results)


# ============================================
# KHỞI CHẠY ỨNG DỤNG
# ============================================

if __name__ == '__main__':
    print("="*60)
    print("  HỆ THỐNG THƯ VIỆN - FLASK + POSTGRESQL + OOP")
    print("="*60)
    print("\n✅ Server: http://127.0.0.1:5000")
    print("\n📌 Tài khoản mẫu:")
    print("   Admin: admin / admin123")
    print("   User:  user1 / user123")
    print("="*60)
    
    # Chạy Flask server
    # debug=True: tự động reload khi code thay đổi
    # port=5000: chạy trên cổng 5000
    app.run(debug=True, port=5000)