from flask import Flask, request, redirect, url_for, render_template, flash
import pymysql

app = Flask(__name__)
app.secret_key = 'your_secret_key'

class InventoryManager:
    def __init__(self):
        self.connection = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='bigup9',
            database='mydatabase'
        )
        self.create_tables()

    def create_tables(self):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    contact_info VARCHAR(255) NOT NULL,
                    UNIQUE KEY unique_name (name)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    supplier_id INT,
                    UNIQUE KEY unique_name (name),
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
                )
            """)
            self.connection.commit()

    def add_supplier(self, name, contact_info):
        with self.connection.cursor() as cursor:
            sql = "INSERT INTO suppliers (name, contact_info) VALUES (%s, %s)"
            cursor.execute(sql, (name, contact_info))
            self.connection.commit()

    def get_suppliers(self):
        with self.connection.cursor() as cursor:
            sql = "SELECT id, name, contact_info FROM suppliers"
            cursor.execute(sql)
            return cursor.fetchall()

    def delete_supplier(self, supplier_id):
        with self.connection.cursor() as cursor:
            sql = "DELETE FROM suppliers WHERE id = %s"
            cursor.execute(sql, (supplier_id,))
            self.connection.commit()

    def add_part(self, name, quantity, price, supplier_id):
        with self.connection.cursor() as cursor:
            sql = "INSERT INTO parts (name, quantity, price, supplier_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (name, quantity, price, supplier_id))
            self.connection.commit()

    def part_exists(self, name):
        with self.connection.cursor() as cursor:
            sql = "SELECT COUNT(*) FROM parts WHERE name = %s"
            cursor.execute(sql, (name,))
            result = cursor.fetchone()
            return result[0] > 0

    def get_parts(self):
        with self.connection.cursor() as cursor:
            sql = "SELECT p.id, p.name, p.quantity, p.price, s.name AS supplier_name FROM parts p LEFT JOIN suppliers s ON p.supplier_id = s.id"
            cursor.execute(sql)
            return cursor.fetchall()

    def delete_part(self, part_id):
        with self.connection.cursor() as cursor:
            sql = "DELETE FROM parts WHERE id = %s"
            cursor.execute(sql, (part_id,))
            self.connection.commit()

    def close_connection(self):
        self.connection.close()

inventory_manager = InventoryManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/suppliers')
def suppliers():
    suppliers = inventory_manager.get_suppliers()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/add_supplier', methods=['POST'])
def add_supplier():
    name = request.form['name']
    contact_info = request.form['contact_info']
    if any(supplier[1] == name for supplier in inventory_manager.get_suppliers()):
        flash('供應商名稱已存在', 'warning')
    else:
        inventory_manager.add_supplier(name, contact_info)
        flash('供應商已成功新增', 'success')
    return redirect(url_for('suppliers'))

@app.route('/delete_supplier/<int:id>')
def delete_supplier(id):
    inventory_manager.delete_supplier(id)
    flash('供應商已成功刪除', 'success')
    return redirect(url_for('suppliers'))

@app.route('/parts')
def parts():
    parts = inventory_manager.get_parts()
    suppliers = inventory_manager.get_suppliers()
    return render_template('parts.html', parts=parts, suppliers=suppliers)

@app.route('/add_part', methods=['POST'])
def add_part():
    name = request.form['name']
    quantity = request.form['quantity']
    price = request.form['price']
    supplier_id = request.form['supplier_id']
    if inventory_manager.part_exists(name):
        flash('零件名稱已存在', 'warning')
    else:
        inventory_manager.add_part(name, int(quantity), float(price), int(supplier_id))
        flash('零件已成功新增', 'success')
    return redirect(url_for('parts'))

@app.route('/delete_part/<int:id>')
def delete_part(id):
    inventory_manager.delete_part(id)
    flash('零件已成功刪除', 'success')
    return redirect(url_for('parts'))

if __name__ == '__main__':  # 檢查此模組是否是直接被執行，而非被匯入
    app.run(host='0.0.0.0',debug=True,port=5000)  # 啟動 Flask 開發伺服器，並啟用 debug 模式以便於除錯
