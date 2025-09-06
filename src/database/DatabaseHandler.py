import sqlite3
from typing import List,Dict,Optional
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
        self.create_laser_tables()
        # Base creates (first run)
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,              -- sale price
                stock INTEGER NOT NULL
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_price REAL NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            '''
        )

        # ---- Migrations ----
        # products: add purchase_price (cost)
        self._ensure_column(cursor, 'products', 'purchase_price', 'REAL NOT NULL DEFAULT 0')
        # orders: add unit prices snapshot
        self._ensure_column(cursor, 'orders', 'unit_purchase_price', 'REAL')
        self._ensure_column(cursor, 'orders', 'unit_sale_price', 'REAL')

        # Backfill reasonable defaults
        cursor.execute(
            "UPDATE products SET purchase_price = price WHERE (purchase_price IS NULL OR purchase_price = 0)"
        )
        cursor.execute(
            '''
            UPDATE orders
            SET unit_sale_price = COALESCE(unit_sale_price, CASE WHEN quantity != 0 THEN total_price * 1.0 / quantity ELSE NULL END)
            '''
        )
        cursor.execute(
            '''
            UPDATE orders
            SET unit_purchase_price = COALESCE(
                unit_purchase_price,
                (SELECT p.purchase_price FROM products p WHERE p.id = orders.product_id)
            )
            '''
        )

        conn.commit()
        conn.close()

    # ---------- Products ----------
    def add_product(self, name: str, purchase_price: float, sale_price: float, stock: int) -> bool:
        """Add a new product to the database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO products (name, purchase_price, price, stock) VALUES (?, ?, ?, ?)",
                (name, float(purchase_price), float(sale_price), int(stock))
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception:
            return False

    def remove_product(self, product_id: int) -> bool:
        """Remove a product from the database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0
        except Exception:
            return False

    def update_product(
        self,
        product_id: int,
        name: str = None,
        purchase_price: float = None,
        sale_price: float = None,
        stock: int = None,
    ) -> bool:
        """Update product information"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            updates, params = [], []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if purchase_price is not None:
                updates.append("purchase_price = ?")
                params.append(float(purchase_price))
            if sale_price is not None:
                updates.append("price = ?")
                params.append(float(sale_price))
            if stock is not None:
                updates.append("stock = ?")
                params.append(int(stock))

            if updates:
                query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
                params.append(product_id)
                cursor.execute(query, params)
                conn.commit()

            conn.close()
            return True
        except Exception:
            return False

    def get_all_products(self) -> List[Dict]:
        """Get all products"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, purchase_price, price AS sale_price, stock FROM products")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_product_by_name(self, name: str) -> Optional[Dict]:
        """Get product by name"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, purchase_price, price AS sale_price, stock FROM products WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ---------- Orders ----------
    def add_order(self, product_id: int, name: str, quantity: int) -> bool:
        """Add a new order and deduct stock. Uses current product prices and snapshots them on the order."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Get product info
            cursor.execute(
                "SELECT price AS sale_price, purchase_price, stock FROM products WHERE id = ?",
                (product_id,),
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False

            sale_price, purchase_price, stock = row
            if int(quantity) > int(stock):
                conn.close()
                return False

            total_price = float(sale_price) * int(quantity)
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Insert order with price snapshots
            cursor.execute(
                '''
                INSERT INTO orders (product_id, name, quantity, total_price, date, unit_purchase_price, unit_sale_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    product_id,
                    name,
                    int(quantity),
                    total_price,
                    date,
                    float(purchase_price),
                    float(sale_price),
                ),
            )

            # Deduct stock
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (int(quantity), product_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def remove_order(self, order_id: int) -> bool:
        """Remove an order from the database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0
        except Exception:
            return False

    def update_order(
        self,
        order_id: int,
        product_id: int = None,
        name: str = None,
        quantity: int = None,
        total_price: float = None,
    ) -> bool:
        """Update order information (does not change stock)."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            updates, params = [], []
            if product_id is not None:
                updates.append("product_id = ?")
                params.append(product_id)
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if quantity is not None:
                updates.append("quantity = ?")
                params.append(quantity)
            if total_price is not None:
                updates.append("total_price = ?")
                params.append(total_price)

            if updates:
                query = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"
                params.append(order_id)
                cursor.execute(query, params)
                conn.commit()

            conn.close()
            return True
        except Exception:
            return False

    def get_all_orders(self) -> List[Dict]:
        """Get all orders with product names"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT o.id, o.product_id, o.name, o.quantity, o.total_price, o.date,
                   o.unit_purchase_price, o.unit_sale_price,
                   p.name AS product_name
            FROM orders o
            JOIN products p ON o.product_id = p.id
            ORDER BY o.date DESC, o.id DESC
            '''
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_analytics_data(self) -> Dict:
        """Get analytics data for dashboard, including profit/loss."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Total revenue
        cursor.execute("SELECT SUM(total_price) FROM orders")
        total_revenue = cursor.fetchone()[0] or 0.0

        # COGS based on snapshot purchase price
        cursor.execute("SELECT SUM(quantity * COALESCE(unit_purchase_price, 0)) FROM orders")
        total_cogs = cursor.fetchone()[0] or 0.0

        total_profit = float(total_revenue) - float(total_cogs)

        # Total loss for items sold below cost
        cursor.execute(
            '''
            SELECT SUM(quantity * (unit_purchase_price - unit_sale_price))
            FROM orders
            WHERE unit_sale_price < unit_purchase_price
            '''
        )
        total_loss = cursor.fetchone()[0] or 0.0

        # Total orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]

        # Products count
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]

        # Low stock products (less than 10)
        cursor.execute("SELECT COUNT(*) FROM products WHERE stock < 10")
        low_stock_count = cursor.fetchone()[0]

        # Recent orders (last 7 days)
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM orders WHERE date > ?", (seven_days_ago,))
        recent_orders = cursor.fetchone()[0]

        # Top selling products
        cursor.execute(
            '''
            SELECT p.name, SUM(o.quantity) as total_sold
            FROM orders o
            JOIN products p ON o.product_id = p.id
            GROUP BY p.id, p.name
            ORDER BY total_sold DESC
            LIMIT 5
            '''
        )
        top_products = cursor.fetchall()

        conn.close()

        return {
            "total_revenue": float(total_revenue),
            "total_cogs": float(total_cogs),
            "total_profit": float(total_profit),
            "total_loss": float(total_loss),
            "total_orders": total_orders,
            "products_count": products_count,
            "low_stock_count": low_stock_count,
            "recent_orders": recent_orders,
            "top_products": [{"name": p[0], "sold": p[1]} for p in top_products],
        }
    def create_laser_tables(self):
        """Create laser machine tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Laser materials table - simplified for laser machine needs
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS laser_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                material_side TEXT NOT NULL,      -- "وش" or "ظهر"
                purchase_price REAL NOT NULL,
                sale_price REAL NOT NULL,
                stock_quantity REAL NOT NULL DEFAULT 0,  -- current stock
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        
        # Laser transactions table
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS laser_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL, -- purchase, sale, return, waste
                customer_name TEXT,             -- for sales only
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES laser_materials (id)
            )
            '''
        )
        
        conn.commit()
        conn.close()

    # Laser Materials Methods
    def add_laser_material(self, name: str, material_side: str, 
                        purchase_price: float, sale_price: float, 
                        initial_quantity: float = 0, notes: str = "") -> bool:
        """Add new laser material"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                '''
                INSERT INTO laser_materials 
                (name, material_side, purchase_price, sale_price, stock_quantity)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (name, material_side, float(purchase_price), float(sale_price), float(initial_quantity))
            )
            
            # If initial quantity > 0, add purchase transaction
            if initial_quantity > 0:
                material_id = cursor.lastrowid
                date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    '''
                    INSERT INTO laser_transactions 
                    (material_id, transaction_type, quantity, unit_price, total_amount, date, notes)
                    VALUES (?, 'purchase', ?, ?, ?, ?, ?)
                    ''',
                    (material_id, float(initial_quantity), float(purchase_price), 
                    float(purchase_price * initial_quantity), date, notes or "Initial stock")
                )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception:
            return False

    def get_all_laser_materials(self) -> List[Dict]:
        """Get all laser materials"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT id, name, material_side, purchase_price, sale_price, stock_quantity
            FROM laser_materials
            ORDER BY name, material_side
            '''
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_laser_material(self, material_id: int, **kwargs) -> bool:
        """Update laser material"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            updates, params = [], []
            for key, value in kwargs.items():
                if value is not None and key in ['name', 'material_side', 'purchase_price', 'sale_price', 'stock_quantity']:
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            if updates:
                query = f"UPDATE laser_materials SET {', '.join(updates)} WHERE id = ?"
                params.append(material_id)
                cursor.execute(query, params)
                conn.commit()
            
            conn.close()
            return True
        except Exception:
            return False

    def delete_laser_material(self, material_id: int) -> bool:
        """Delete laser material and its transactions"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Delete transactions first (foreign key constraint)
            cursor.execute("DELETE FROM laser_transactions WHERE material_id = ?", (material_id,))
            
            # Delete material
            cursor.execute("DELETE FROM laser_materials WHERE id = ?", (material_id,))
            
            conn.commit()
            affected = cursor.rowcount > 0
            conn.close()
            return affected
        except Exception:
            return False

    def add_laser_transaction(self, material_id: int, transaction_type: str, 
                            quantity: float, customer_name: str = "", notes: str = "") -> bool:
        """Add laser transaction (purchase, sale, return, waste)"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Get current material info
            cursor.execute(
                "SELECT stock_quantity, sale_price, purchase_price FROM laser_materials WHERE id = ?",
                (material_id,)
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
            
            current_stock, sale_price, purchase_price = row
            
            # Calculate price and new stock based on transaction type
            if transaction_type == 'purchase':
                unit_price = purchase_price
                new_stock = current_stock + quantity
                total_amount = unit_price * quantity
            elif transaction_type == 'sale':
                unit_price = sale_price
                if quantity > current_stock:
                    conn.close()
                    return False
                new_stock = current_stock - quantity
                total_amount = unit_price * quantity
            elif transaction_type == 'return':
                unit_price = sale_price  # Return at sale price
                new_stock = current_stock + quantity
                total_amount = unit_price * quantity
            elif transaction_type == 'waste':
                unit_price = purchase_price  # Loss at purchase price
                if quantity > current_stock:
                    conn.close()
                    return False
                new_stock = current_stock - quantity
                total_amount = unit_price * quantity  # This represents the loss value
            else:
                conn.close()
                return False
            
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add transaction
            cursor.execute(
                '''
                INSERT INTO laser_transactions 
                (material_id, transaction_type, customer_name, quantity, unit_price, total_amount, date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (material_id, transaction_type, customer_name, quantity, unit_price, total_amount, date, notes)
            )
            
            # Update stock
            cursor.execute(
                "UPDATE laser_materials SET stock_quantity = ? WHERE id = ?",
                (new_stock, material_id)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def get_laser_transactions(self) -> List[Dict]:
        """Get all laser transactions"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT t.id, t.transaction_type, t.customer_name, t.quantity, t.unit_price, 
                t.total_amount, t.date, t.notes,
                m.name as material_name, m.material_side
            FROM laser_transactions t
            JOIN laser_materials m ON t.material_id = m.id
            ORDER BY t.date DESC, t.id DESC
            '''
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_laser_analytics(self) -> Dict:
        """Get laser machine analytics"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Total purchases (money spent buying materials)
        cursor.execute(
            "SELECT SUM(total_amount) FROM laser_transactions WHERE transaction_type = 'purchase'"
        )
        total_purchases = cursor.fetchone()[0] or 0.0
        
        # Total sales (money earned from sales)
        cursor.execute(
            "SELECT SUM(total_amount) FROM laser_transactions WHERE transaction_type = 'sale'"
        )
        total_sales = cursor.fetchone()[0] or 0.0
        
        # Total returns (money returned to customers)
        cursor.execute(
            "SELECT SUM(total_amount) FROM laser_transactions WHERE transaction_type = 'return'"
        )
        total_returns = cursor.fetchone()[0] or 0.0
        
        # Total waste (value of wasted materials)
        cursor.execute(
            "SELECT SUM(total_amount) FROM laser_transactions WHERE transaction_type = 'waste'"
        )
        total_waste = cursor.fetchone()[0] or 0.0
        
        # Calculate profit/loss
        net_sales = total_sales - total_returns
        net_profit = net_sales - total_purchases - total_waste
        
        # Material counts
        cursor.execute("SELECT COUNT(*) FROM laser_materials")
        materials_count = cursor.fetchone()[0]
        
        # Low stock materials (less than 10 units)
        cursor.execute("SELECT COUNT(*) FROM laser_materials WHERE stock_quantity < 10")
        low_stock_count = cursor.fetchone()[0]
        
        # Recent transactions count (last 7 days)
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COUNT(*) FROM laser_transactions WHERE date > ?",
            (seven_days_ago,)
        )
        recent_transactions = cursor.fetchone()[0]
        
        # Top selling materials
        cursor.execute(
            '''
            SELECT m.name, m.material_side, SUM(t.quantity) as total_sold
            FROM laser_transactions t
            JOIN laser_materials m ON t.material_id = m.id
            WHERE t.transaction_type = 'sale'
            GROUP BY m.id, m.name, m.material_side
            ORDER BY total_sold DESC
            LIMIT 5
            '''
        )
        top_materials = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_purchases": float(total_purchases),
            "total_sales": float(total_sales),
            "total_returns": float(total_returns),
            "total_waste": float(total_waste),
            "net_sales": float(net_sales),
            "net_profit": float(net_profit),
            "materials_count": materials_count,
            "low_stock_count": low_stock_count,
            "recent_transactions": recent_transactions,
            "top_materials": [{"name": f"{m[0]} ({m[1]})", "sold": m[2]} for m in top_materials],
        }