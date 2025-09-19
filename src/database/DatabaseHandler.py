import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
import sys

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DatabaseHandler:
    def __init__(self, db_name: str = "data/venom_shop.db"):
        self.db_name = resource_path(db_name)
        os.makedirs(os.path.dirname(self.db_name), exist_ok=True)
        self.create_database()

    def _ensure_column(self, cursor, table: str, column: str, decl: str):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cursor.fetchall()]
        if column not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def create_database(self):
        """Create database and tables if they don't exist, and migrate schema if needed"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Products Table
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                supplier TEXT,
                purchase_date TEXT,
                purchase_price REAL NOT NULL,
                sale_price REAL,
                stock INTEGER NOT NULL,
                notes TEXT,
                UNIQUE(name, purchase_price)
            )
            '''
        )

        # Operations Table (replaces Orders)
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                laser_material_id INTEGER,
                operation_type TEXT NOT NULL, -- sale, return, waste
                customer_name TEXT,
                customer_phone TEXT,
                quantity REAL NOT NULL,
                total_price REAL NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (laser_material_id) REFERENCES laser_materials (id)
            )
            '''
        )

        # Laser Materials Table
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS laser_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                material_side TEXT NOT NULL, -- 'وش' or 'ظهر'
                supplier TEXT,
                purchase_date TEXT,
                purchase_price REAL NOT NULL,
                sale_price REAL,
                stock_quantity REAL NOT NULL DEFAULT 0,
                notes TEXT,
                UNIQUE(name, material_side, purchase_price)
            )
            '''
        )
        conn.commit()
        conn.close()

    # ---------- Products ----------
    def add_product(self, name: str, supplier: Optional[str], purchase_date: str, purchase_price: float, stock: int) -> bool:
        """Add a new product to the database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO products (name, supplier, purchase_date, purchase_price, stock) VALUES (?, ?, ?, ?, ?)",
                (name, supplier, purchase_date, float(purchase_price), int(stock))
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
        except Exception:
            conn.close()
            return False


    def get_product_by_name_and_price(self, name: str, purchase_price: float) -> Optional[Dict]:
        """Get product by name and purchase price"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE name = ? AND purchase_price = ?",
            (name, purchase_price),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


    def update_product_stock(self, product_id: int, quantity_change: int) -> bool:
        """Update product stock"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (quantity_change, product_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False


    def get_all_products(self) -> List[Dict]:
        """Get all products"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_product(self, product_id: int, name: str, supplier: str, purchase_price: float, sale_price: float, stock: int, notes: str) -> bool:
        """Update product information"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE products SET name = ?, supplier = ?, purchase_price = ?, sale_price = ?, stock = ?, notes = ? WHERE id = ?",
                (name, supplier, purchase_price, sale_price, stock, notes, product_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def delete_product(self, product_id: int) -> bool:
        """Delete a product"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM operations WHERE product_id = ?", (product_id,))
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    # ---------- Laser Materials ----------
    def add_laser_material(self, name: str, material_side: str, supplier: Optional[str], purchase_date: str, purchase_price: float, stock_quantity: float) -> bool:
        """Add a new laser material"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO laser_materials (name, material_side, supplier, purchase_date, purchase_price, stock_quantity) VALUES (?, ?, ?, ?, ?, ?)",
                (name, material_side, supplier, purchase_date, purchase_price, stock_quantity)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception:
            return False

    def get_laser_material_by_name_side_price(self, name: str, material_side: str, purchase_price: float) -> Optional[Dict]:
        """Get laser material by name, side, and purchase price"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM laser_materials WHERE name = ? AND material_side = ? AND purchase_price = ?",
            (name, material_side, purchase_price),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


    def update_laser_material_stock(self, material_id: int, quantity_change: float) -> bool:
        """Update laser material stock"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE laser_materials SET stock_quantity = stock_quantity + ? WHERE id = ?",
                (quantity_change, material_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False


    def get_all_laser_materials(self) -> List[Dict]:
        """Get all laser materials"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM laser_materials ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_laser_material(self, material_id: int, name: str, material_side: str, supplier: str, purchase_price: float, sale_price: float, stock_quantity: float, notes: str) -> bool:
        """Update laser material information"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE laser_materials SET name = ?, material_side = ?, supplier = ?, purchase_price = ?, sale_price = ?, stock_quantity = ?, notes = ? WHERE id = ?",
                (name, material_side, supplier, purchase_price, sale_price, stock_quantity, notes, material_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def delete_laser_material(self, material_id: int) -> bool:
        """Delete a laser material"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM operations WHERE laser_material_id = ?", (material_id,))
            cursor.execute("DELETE FROM laser_materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    # ---------- Operations ----------
    def add_operation(self, item_id: int, item_type: str, operation_type: str, customer_name: str, customer_phone: Optional[str], quantity: float, total_price: float) -> bool:
        """Add a new operation (sale, return, waste) and update stock in a single transaction."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            product_id = item_id if item_type == 'product' else None
            laser_material_id = item_id if item_type == 'laser' else None

            cursor.execute(
                "INSERT INTO operations (product_id, laser_material_id, operation_type, customer_name, customer_phone, quantity, total_price, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (product_id, laser_material_id, operation_type, customer_name, customer_phone, quantity, total_price, date)
            )

            # Adjust stock within the same transaction
            stock_change = -quantity if operation_type in ['بيع', 'تالف'] else quantity
            if item_type == 'product':
                cursor.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (stock_change, product_id)
                )
            elif item_type == 'laser':
                cursor.execute(
                    "UPDATE laser_materials SET stock_quantity = stock_quantity + ? WHERE id = ?",
                    (stock_change, laser_material_id)
                )

            conn.commit()
            return True
        except Exception as e:
            print(f"Error in add_operation: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_all_operations(self) -> List[Dict]:
        """Get all operations with item names"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT o.id, o.date, o.operation_type,
                   CASE
                       WHEN o.product_id IS NOT NULL THEN p.name
                       WHEN o.laser_material_id IS NOT NULL THEN lm.name || ' (' || lm.material_side || ')'
                   END as item_name,
                   o.quantity, o.total_price, o.customer_name
            FROM operations o
            LEFT JOIN products p ON o.product_id = p.id
            LEFT JOIN laser_materials lm ON o.laser_material_id = lm.id
            ORDER BY o.date DESC
            '''
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---------- Analytics ----------
    def get_analytics_data(self, start_date: str, end_date: str) -> Dict:
        """Get analytics data for a specific period."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # --- Shop Analytics ---
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN operation_type = 'بيع' THEN total_price ELSE 0 END) -
                SUM(CASE WHEN operation_type = 'استرجاع' THEN total_price ELSE 0 END)
            FROM operations
            WHERE product_id IS NOT NULL AND date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        )
        shop_revenue = cursor.fetchone()[0] or 0.0

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN o.operation_type = 'بيع' THEN o.quantity * p.purchase_price ELSE 0 END) -
                SUM(CASE WHEN o.operation_type = 'استرجاع' THEN o.quantity * p.purchase_price ELSE 0 END)
            FROM operations o
            JOIN products p ON o.product_id = p.id
            WHERE o.product_id IS NOT NULL AND o.date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        )
        shop_cogs = cursor.fetchone()[0] or 0.0
        
        cursor.execute(
            """
            SELECT SUM(o.quantity * p.purchase_price)
            FROM operations o
            JOIN products p ON o.product_id = p.id
            WHERE o.operation_type = 'تالف' AND o.product_id IS NOT NULL AND o.date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        )
        shop_waste_cost = cursor.fetchone()[0] or 0.0
        shop_profit = shop_revenue - shop_cogs - shop_waste_cost

        # --- Laser Analytics ---
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN operation_type = 'بيع' THEN total_price ELSE 0 END) -
                SUM(CASE WHEN operation_type = 'استرجاع' THEN total_price ELSE 0 END)
            FROM operations
            WHERE laser_material_id IS NOT NULL AND date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        )
        laser_revenue = cursor.fetchone()[0] or 0.0

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN o.operation_type = 'بيع' THEN o.quantity * lm.purchase_price ELSE 0 END) -
                SUM(CASE WHEN o.operation_type = 'استرجاع' THEN o.quantity * lm.purchase_price ELSE 0 END)
            FROM operations o
            JOIN laser_materials lm ON o.laser_material_id = lm.id
            WHERE o.laser_material_id IS NOT NULL AND o.date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        )
        laser_cogs = cursor.fetchone()[0] or 0.0
        
        cursor.execute(
            """
            SELECT SUM(o.quantity * lm.purchase_price)
            FROM operations o
            JOIN laser_materials lm ON o.laser_material_id = lm.id
            WHERE o.operation_type = 'تالف' AND o.laser_material_id IS NOT NULL AND o.date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        )
        laser_waste_cost = cursor.fetchone()[0] or 0.0
        laser_profit = laser_revenue - laser_cogs - laser_waste_cost

        top_selling = self.get_top_selling_items(start_date, end_date)
        conn.close()

        return {
            "shop_revenue": shop_revenue,
            "shop_profit": shop_profit,
            "laser_revenue": laser_revenue,
            "laser_profit": laser_profit,
            "top_shop_products": top_selling["top_shop_products"],
            "top_laser_materials": top_selling["top_laser_materials"]
        }

    def get_top_selling_items(self, start_date: str, end_date: str) -> Dict:
        """Get top selling items for a specific period, accounting for returns."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Top Shop Products
        cursor.execute(
            """
            SELECT
                p.name,
                SUM(CASE WHEN o.operation_type = 'بيع' THEN o.quantity ELSE 0 END) -
                SUM(CASE WHEN o.operation_type = 'استرجاع' THEN o.quantity ELSE 0 END) as total_sold
            FROM operations o
            JOIN products p ON o.product_id = p.id
            WHERE o.date BETWEEN ? AND ?
            GROUP BY p.name
            HAVING total_sold > 0
            ORDER BY total_sold DESC
            LIMIT 5
            """,
            (start_date, end_date)
        )
        top_shop_products = [dict(row) for row in cursor.fetchall()]

        # Top Laser Materials
        cursor.execute(
            """
            SELECT
                lm.name || ' (' || lm.material_side || ')' as name,
                SUM(CASE WHEN o.operation_type = 'بيع' THEN o.quantity ELSE 0 END) -
                SUM(CASE WHEN o.operation_type = 'استرجاع' THEN o.quantity ELSE 0 END) as total_sold
            FROM operations o
            JOIN laser_materials lm ON o.laser_material_id = lm.id
            WHERE o.date BETWEEN ? AND ?
            GROUP BY lm.name, lm.material_side
            HAVING total_sold > 0
            ORDER BY total_sold DESC
            LIMIT 5
            """,
            (start_date, end_date)
        )
        top_laser_materials = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return {
            "top_shop_products": top_shop_products,
            "top_laser_materials": top_laser_materials,
        }

