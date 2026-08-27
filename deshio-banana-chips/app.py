from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, secrets
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
DB = os.path.join(os.path.dirname(__file__), "banana_bliss.db")

CATEGORIES = [
    ("All", "all", "🛍️"),
    ("Classic", "classic", "🥔"),
    ("Masala", "masala", "🌶️"),
    ("Spicy", "spicy", "🔥"),
    ("Combo Packs", "combo", "🎁"),
    ("Family Packs", "family", "📦"),
]

SEED_PRODUCTS = [
    (1,"Classic Salted Banana Chips","classic",99,129,"200 g","🥔","BESTSELLER","Thin, golden and lightly salted. A timeless crunchy snack.",1),
    (2,"Kerala Style Banana Chips","classic",119,149,"250 g","🍌","POPULAR","Traditional-style crispy banana slices with a balanced savoury taste.",1),
    (3,"Chatpata Masala Chips","masala",109,139,"200 g","🌶️","TRENDING","Crispy banana chips tossed with a punchy Indian masala blend.",1),
    (4,"Peri Peri Banana Chips","spicy",119,149,"200 g","🔥","NEW","Tangy, spicy and bold for serious snack lovers.",1),
    (5,"Family Crunch Combo","combo",299,369,"600 g","🎁","DEAL","Three flavours packed together for sharing, parties and gifting.",1),
    (6,"Big Snack Family Pack","family",449,549,"1 kg","📦","VALUE","A generous 1 kg pack for homes, offices and celebrations.",1),
    (7,"Masala Mini Pack","masala",59,79,"100 g","🌶️","VALUE","A convenient pocket-size pack for quick snacking.",1),
    (8,"Classic Party Pack","combo",199,249,"400 g","🎉","DEAL","Crispy classic chips for movie nights and get-togethers.",1),
]

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      phone TEXT, password TEXT NOT NULL,
      is_admin INTEGER DEFAULT 0, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
      price REAL NOT NULL, mrp REAL NOT NULL, weight TEXT NOT NULL,
      emoji TEXT NOT NULL, badge TEXT, description TEXT NOT NULL,
      stock INTEGER DEFAULT 0, active INTEGER DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT UNIQUE NOT NULL,
      user_id INTEGER, name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT,
      address TEXT NOT NULL, city TEXT NOT NULL, pincode TEXT NOT NULL,
      payment TEXT NOT NULL, subtotal REAL NOT NULL, shipping REAL NOT NULL,
      total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
      created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS order_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
      product_id INTEGER NOT NULL, name TEXT NOT NULL, price REAL NOT NULL,
      quantity INTEGER NOT NULL, weight TEXT NOT NULL,
      FOREIGN KEY(order_id) REFERENCES orders(id)
    );
    CREATE TABLE IF NOT EXISTS wishlist(
      user_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
      PRIMARY KEY(user_id, product_id),
      FOREIGN KEY(user_id) REFERENCES users(id),
      FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)
    if c.execute("SELECT COUNT(*) n FROM products").fetchone()["n"] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        c.executemany("""INSERT INTO products
        (id,name,category,price,mrp,weight,emoji,badge,description,stock,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""", [x[:-1]+(now,) if False else (*x, now) for x in SEED_PRODUCTS])
    # Seed admin account. Change credentials immediately in production.
    if not c.execute("SELECT 1 FROM users WHERE email=?", ("admin@bananabliss.in",)).fetchone():
        c.execute("""INSERT INTO users(name,email,phone,password,is_admin,created_at)
                    VALUES(?,?,?,?,?,?)""",
                  ("Banana Bliss Admin","admin@bananabliss.in","9999999999",
                   generate_password_hash("Admin@123"),1,datetime.now().isoformat(timespec="seconds")))
    c.commit(); c.close()

def current_user():
    uid = session.get("user_id")
    if not uid: return None
    c=connect(); u=c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone(); c.close()
    return u

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user():
            flash("Please login to continue.","warning")
            return redirect(url_for("login", next=request.path))
        return fn(*a, **kw)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        u=current_user()
        if not u or not u["is_admin"]:
            flash("Admin access required.","warning")
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper

def cart_items():
    cart=session.get("cart", {})
    if not cart: return [],0,0
    c=connect(); items=[]; subtotal=0; count=0
    for pid,q in cart.items():
        p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(int(pid),)).fetchone()
        if p:
            q=max(0,min(int(q),p["stock"]))
            if q:
                sub=p["price"]*q; subtotal+=sub; count+=q
                items.append({**dict(p),"quantity":q,"subtotal":sub})
    c.close(); return items,round(subtotal,2),count

@app.context_processor
def inject():
    _,sub,count=cart_items()
    return {"cart_count":count,"current_user":current_user(),"categories":CATEGORIES}

@app.route("/")
def home():
    c=connect()
    products=[dict(x) for x in c.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()]
    c.close()
    return render_template("home.html", products=products)

@app.route("/products")
def products():
    q=request.args.get("q","").strip(); cat=request.args.get("category","all")
    sort=request.args.get("sort","popular")
    sql="SELECT * FROM products WHERE active=1"; args=[]
    if q: sql+=" AND (name LIKE ? OR description LIKE ?)"; args += [f"%{q}%",f"%{q}%"]
    if cat!="all": sql+=" AND category=?"; args.append(cat)
    order={"low":"price ASC","high":"price DESC","new":"id DESC"}.get(sort,"id ASC")
    sql+=" ORDER BY "+order
    c=connect(); ps=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close()
    return render_template("products.html",products=ps,q=q,cat=cat,sort=sort)

@app.route("/product/<int:pid>")
def product(pid):
    c=connect(); p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(pid,)).fetchone()
    related=c.execute("SELECT * FROM products WHERE active=1 AND id!=? AND category=? LIMIT 4",(pid,p["category"] if p else "")).fetchall() if p else []
    c.close()
    if not p: return "Product not found",404
    return render_template("product.html",p=p,related=related)

@app.post("/api/cart")
def api_cart():
    data=request.get_json() or {}; pid=str(data.get("product_id")); action=data.get("action","set")
    c=connect(); p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(int(pid),)).fetchone(); c.close()
    if not p: return jsonify(ok=False,error="Product unavailable"),404
    cart=session.get("cart",{}); old=int(cart.get(pid,0))
    if action=="add": q=old+int(data.get("quantity",1))
    elif action=="inc": q=old+1
    elif action=="dec": q=old-1
    else: q=int(data.get("quantity",0))
    q=max(0,min(q,p["stock"]))
    if q: cart[pid]=q
    else: cart.pop(pid,None)
    session["cart"]=cart
    items,sub,count=cart_items()
    return jsonify(ok=True,subtotal=sub,count=count,items=items)

@app.route("/cart")
def cart():
    items,sub,count=cart_items(); shipping=0 if sub>=499 or sub==0 else 49
    return render_template("cart.html",items=items,subtotal=sub,shipping=shipping,total=sub+shipping)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower()
        phone=request.form.get("phone","").strip(); pw=request.form["password"]
        if len(pw)<6: flash("Password must be at least 6 characters.","warning")
        else:
            c=connect()
            try:
                cur=c.execute("INSERT INTO users(name,email,phone,password,created_at) VALUES(?,?,?,?,?)",
                              (name,email,phone,generate_password_hash(pw),datetime.now().isoformat(timespec="seconds")))
                c.commit(); session["user_id"]=cur.lastrowid; flash("Account created!","success"); return redirect(url_for("home"))
            except sqlite3.IntegrityError: flash("Email already registered.","warning")
            finally: c.close()
    return render_template("auth.html",mode="register")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); pw=request.form["password"]
        c=connect(); u=c.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone(); c.close()
        if u and check_password_hash(u["password"],pw):
            session["user_id"]=u["id"]; flash("Welcome back!","success")
            return redirect(request.args.get("next") or url_for("home"))
        flash("Invalid email or password.","warning")
    return render_template("auth.html",mode="login")

@app.get("/logout")
def logout():
    session.clear(); flash("You have been logged out.","success"); return redirect(url_for("home"))

@app.post("/api/wishlist/<int:pid>")
@login_required
def wishlist_toggle(pid):
    u=current_user(); c=connect()
    exists=c.execute("SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?",(u["id"],pid)).fetchone()
    if exists: c.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?",(u["id"],pid)); state=False
    else: c.execute("INSERT OR IGNORE INTO wishlist VALUES(?,?)",(u["id"],pid)); state=True
    c.commit(); c.close(); return jsonify(ok=True,active=state)

@app.route("/wishlist")
@login_required
def wishlist():
    u=current_user(); c=connect()
    ps=c.execute("""SELECT p.* FROM products p JOIN wishlist w ON p.id=w.product_id
                    WHERE w.user_id=? AND p.active=1""",(u["id"],)).fetchall(); c.close()
    return render_template("wishlist.html",products=ps)

@app.route("/checkout",methods=["GET","POST"])
@login_required
def checkout():
    items,sub,_=cart_items()
    if not items: return redirect(url_for("cart"))
    shipping=0 if sub>=499 else 49; total=sub+shipping; u=current_user()
    if request.method=="POST":
        fields=["name","phone","address","city","pincode","payment"]
        if any(not request.form.get(x,"").strip() for x in fields):
            flash("Please fill all required fields.","warning")
        else:
            c=connect(); now=datetime.now().isoformat(timespec="seconds")
            no="BB-"+datetime.now().strftime("%Y%m%d")+"-"+secrets.token_hex(3).upper()
            cur=c.execute("""INSERT INTO orders(order_no,user_id,name,phone,email,address,city,pincode,payment,subtotal,shipping,total,status,created_at)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (no,u["id"],request.form["name"].strip(),request.form["phone"].strip(),request.form.get("email","").strip(),
                          request.form["address"].strip(),request.form["city"].strip(),request.form["pincode"].strip(),
                          request.form["payment"],sub,shipping,total,"Pending",now))
            oid=cur.lastrowid
            for i in items:
                c.execute("""INSERT INTO order_items(order_id,product_id,name,price,quantity,weight) VALUES(?,?,?,?,?,?)""",
                          (oid,i["id"],i["name"],i["price"],i["quantity"],i["weight"]))
                c.execute("UPDATE products SET stock=stock-? WHERE id=?",(i["quantity"],i["id"]))
            c.commit(); c.close(); session["cart"]={}; return redirect(url_for("order_success",order_no=no))
    return render_template("checkout.html",items=items,subtotal=sub,shipping=shipping,total=total,user=u)

@app.route("/order-success/<order_no>")
@login_required
def order_success(order_no):
    c=connect(); o=c.execute("SELECT * FROM orders WHERE order_no=? AND user_id=?",(order_no,current_user()["id"])).fetchone(); c.close()
    if not o:return "Order not found",404
    return render_template("success.html",order=o)

@app.route("/orders")
@login_required
def orders():
    c=connect(); osx=c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",(current_user()["id"],)).fetchall(); c.close()
    return render_template("orders.html",orders=osx)

@app.route("/order/<order_no>")
@login_required
def order_detail(order_no):
    c=connect(); o=c.execute("SELECT * FROM orders WHERE order_no=? AND user_id=?",(order_no,current_user()["id"])).fetchone()
    if not o:return "Order not found",404
    its=c.execute("SELECT * FROM order_items WHERE order_id=?",(o["id"],)).fetchall(); c.close()
    return render_template("order_detail.html",order=o,items=its)

@app.route("/admin")
@admin_required
def admin():
    c=connect()
    stats={
      "orders":c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"],
      "revenue":c.execute("SELECT COALESCE(SUM(total),0) n FROM orders WHERE status!='Cancelled'").fetchone()["n"],
      "customers":c.execute("SELECT COUNT(*) n FROM users WHERE is_admin=0").fetchone()["n"],
      "products":c.execute("SELECT COUNT(*) n FROM products WHERE active=1").fetchone()["n"],
    }
    orders=c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    products=c.execute("SELECT * FROM products ORDER BY id").fetchall()
    c.close(); return render_template("admin.html",stats=stats,orders=orders,products=products)

@app.post("/admin/order/<int:oid>/status")
@admin_required
def admin_status(oid):
    status=request.form["status"]
    if status not in {"Pending","Confirmed","Packed","Shipped","Delivered","Cancelled"}: return "Bad status",400
    c=connect(); c.execute("UPDATE orders SET status=? WHERE id=?",(status,oid)); c.commit(); c.close()
    flash("Order status updated.","success"); return redirect(url_for("admin"))

@app.post("/admin/product/<int:pid>/stock")
@admin_required
def admin_stock(pid):
    stock=max(0,int(request.form["stock"])); c=connect(); c.execute("UPDATE products SET stock=? WHERE id=?",(stock,pid)); c.commit(); c.close()
    flash("Stock updated.","success"); return redirect(url_for("admin"))

if __name__=="__main__":
    init_db()
    app.run(debug=True,host="0.0.0.0",port=5000)
