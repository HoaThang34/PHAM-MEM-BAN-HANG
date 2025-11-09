from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
import json
import csv
from datetime import datetime
import openpyxl

app = Flask(__name__)
DATA_DIR = "data"

os.makedirs(DATA_DIR, exist_ok=True)

PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
INVENTORY_LOGS_FILE = os.path.join(DATA_DIR, "inventory_logs.json")

# Helper: load JSON an toàn
def load_json(file_path, default):
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except (json.JSONDecodeError, ValueError):
        return default

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Sinh mã vạch (chỉ văn bản, không lưu ảnh)
def generate_barcode(product_id):
    return str(product_id).zfill(8)  # 8 chữ số, ví dụ: 00000001

# ============ Routes ============

@app.route("/")
def index():
    products = load_json(PRODUCTS_FILE, [])
    return render_template("index.html", products=products)

@app.route("/products")
def products_page():
    products = load_json(PRODUCTS_FILE, [])
    return render_template("products.html", products=products)

@app.route("/orders")
def orders_page():
    orders = load_json(ORDERS_FILE, [])
    return render_template("orders.html", orders=orders)

@app.route("/stock_report")
def stock_report():
    products = load_json(PRODUCTS_FILE, [])
    return render_template("stock_report.html", products=products)

@app.route("/inventory_check")
def inventory_check_page():
    products = load_json(PRODUCTS_FILE, [])
    return render_template("inventory_check.html", products=products)

# Thêm sản phẩm (tự động sinh mã vạch)
@app.route("/add_product", methods=["POST"])
def add_product():
    name = request.form["name"].strip()
    price = float(request.form["price"])
    stock = int(request.form["stock"])

    products = load_json(PRODUCTS_FILE, [])
    pid = max([p["id"] for p in products], default=0) + 1
    barcode = generate_barcode(pid)
    products.append({
        "id": pid,
        "name": name,
        "price": price,
        "stock": stock,
        "barcode": barcode
    })
    save_json(PRODUCTS_FILE, products)
    return redirect(url_for("products_page"))

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    file = request.files["csvfile"]
    if not file or not file.filename.endswith('.csv'):
        return "Invalid CSV", 400

    products = load_json(PRODUCTS_FILE, [])
    existing = {p["name"] for p in products}
    max_id = max([p["id"] for p in products], default=0)

    filepath = os.path.join(DATA_DIR, "temp.csv")
    file.save(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"].strip()
            if name in existing: continue
            max_id += 1
            products.append({
                "id": max_id,
                "name": name,
                "price": float(row["price"]),
                "stock": int(row["stock"]),
                "barcode": generate_barcode(max_id)
            })
            existing.add(name)
    os.remove(filepath)
    save_json(PRODUCTS_FILE, products)
    return redirect(url_for("products_page"))

# Thanh toán (lưu khách hàng)
@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json()
    cart = data.get("cart", [])
    customer_name = data.get("customer_name", "").strip()
    customer_phone = data.get("customer_phone", "").strip()

    if not cart:
        return jsonify({"error": "Giỏ hàng trống"}), 400

    # Cập nhật tồn kho
    products = load_json(PRODUCTS_FILE, [])
    product_map = {p["id"]: p for p in products}
    for item in cart:
        pid = item["id"]
        if product_map[pid]["stock"] < item["qty"]:
            return jsonify({"error": f"Hết hàng: {product_map[pid]['name']}"}), 400
        product_map[pid]["stock"] -= item["qty"]
    save_json(PRODUCTS_FILE, list(product_map.values()))

    # Lưu đơn hàng
    orders = load_json(ORDERS_FILE, [])
    order_id = max([o["id"] for o in orders], default=0) + 1
    total = sum(item["price"] * item["qty"] for item in cart)
    orders.append({
        "id": order_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": cart,
        "total": total,
        "customer_name": customer_name,
        "customer_phone": customer_phone
    })
    save_json(ORDERS_FILE, orders)

    # Lưu khách hàng (nếu có)
    if customer_name or customer_phone:
        customers = load_json(CUSTOMERS_FILE, [])
        if not any(c["phone"] == customer_phone for c in customers):
            customers.append({
                "name": customer_name,
                "phone": customer_phone
            })
            save_json(CUSTOMERS_FILE, customers)

    return jsonify({"success": True, "order_id": order_id})

# Kiểm kho: lưu kết quả sau khi nhập số lượng thực tế
@app.route("/submit_inventory", methods=["POST"])
def submit_inventory():
    actual_stock = request.json  # { "1": 10, "2": 5, ... }
    products = load_json(PRODUCTS_FILE, [])
    logs = []

    for p in products:
        pid = str(p["id"])
        system_qty = p["stock"]
        actual_qty = int(actual_stock.get(pid, system_qty))
        diff = actual_qty - system_qty
        if diff != 0:
            logs.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "system_qty": system_qty,
                "actual_qty": actual_qty,
                "diff": diff,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        p["stock"] = actual_qty  # cập nhật tồn kho theo thực tế

    save_json(PRODUCTS_FILE, products)
    all_logs = load_json(INVENTORY_LOGS_FILE, [])
    all_logs.extend(logs)
    save_json(INVENTORY_LOGS_FILE, all_logs)
    return jsonify({"success": True})

# Xuất Excel thống kê doanh thu
@app.route("/export_sales")
def export_sales():
    orders = load_json(ORDERS_FILE, [])
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Doanh thu"
    ws.append(["ID Đơn", "Thời gian", "Khách hàng", "SĐT", "Tổng tiền"])

    for o in orders:
        ws.append([
            o["id"],
            o["timestamp"],
            o.get("customer_name", ""),
            o.get("customer_phone", ""),
            o["total"]
        ])

    filename = f"doanh_thu_{datetime.now().strftime('%Y%m%d')}.xlsx"
    filepath = os.path.join(DATA_DIR, filename)
    wb.save(filepath)
    return send_file(filepath, as_attachment=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)