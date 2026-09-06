"""
JUMIA MANAGEMENT SYSTEM - Complete Backend
SQLite Version for Render Deployment
Run locally: python app.py
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid, random, base64, json, time, os

# ============ CONFIG ============
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
os.makedirs(os.path.join(UPLOAD_FOLDER, 'products'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'categories'), exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'jumia-secret-key-2024')

# Database Configuration - Using SQLite
sqlite_path = os.path.join(basedir, 'jumia_db.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# CORS Configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

db = SQLAlchemy(app)

# ============ HELPERS ============
def now_utc():
    return datetime.now(timezone.utc)

def generate_uuid():
    return str(uuid.uuid4())

def generate_order_number():
    return f"JUM-{now_utc().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def create_token(user_id, role, email, name):
    payload = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'name': name,
        'exp': time.time() + 86400
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()

def decode_token(token):
    try:
        payload = json.loads(base64.b64decode(token.encode()).decode())
        if payload['exp'] < time.time():
            return None
        return payload
    except:
        return None

def token_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        if payload.get('role') != 'ADMIN':
            return jsonify({'error': 'Admin access required'}), 403
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated

def save_image(file, folder='products'):
    if not file:
        return None
    filename = secure_filename(f"{uuid.uuid4().hex[:8]}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    file.save(filepath)
    return f"/uploads/{folder}/{filename}"

# ============ MODELS ============
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now_utc)
    
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f"{self.first_name} {self.last_name}",
            'role': self.role,
            'phone': self.phone,
            'is_active': self.is_active
        }

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(500))
    parent_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_utc)
    
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    products = db.relationship('Product', backref='category', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'image': self.image,
            'parent_id': self.parent_id,
            'is_active': self.is_active,
            'product_count': self.products.count()
        }

class Vendor(db.Model):
    __tablename__ = 'vendors'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    business_name = db.Column(db.String(200), nullable=False)
    business_email = db.Column(db.String(120))
    business_phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Sierra Leone')
    total_sales = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    commission_rate = db.Column(db.Float, default=10.0)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_utc)
    
    user = db.relationship('User', backref='vendor_profile')
    products = db.relationship('Product', backref='vendor', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_name': self.business_name,
            'business_email': self.business_email,
            'business_phone': self.business_phone,
            'city': self.city,
            'total_sales': self.total_sales,
            'total_orders': self.total_orders,
            'commission_rate': self.commission_rate,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'product_count': self.products.count()
        }

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(500))
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    vendor_id = db.Column(db.String(36), db.ForeignKey('vendors.id'))
    main_image = db.Column(db.String(500))
    status = db.Column(db.String(20), default='ACTIVE')
    is_featured = db.Column(db.Boolean, default=False)
    sales_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)
    
    inventory = db.relationship('Inventory', backref='product', uselist=False, cascade='all, delete-orphan')
    
    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.selling_price
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'short_description': self.short_description,
            'cost_price': self.cost_price,
            'selling_price': self.selling_price,
            'current_price': self.current_price,
            'discount_price': self.discount_price,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'vendor_id': self.vendor_id,
            'main_image': self.main_image,
            'status': self.status,
            'is_featured': self.is_featured,
            'sales_count': self.sales_count,
            'average_rating': self.average_rating,
            'inventory': self.inventory.to_dict() if self.inventory else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'))
    warehouse_id = db.Column(db.String(36), db.ForeignKey('warehouses.id'))
    quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    reserved_quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)
    
    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    @property
    def is_low_stock(self):
        return self.available_quantity <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self):
        return self.available_quantity <= 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'warehouse_id': self.warehouse_id,
            'quantity': self.quantity,
            'available_quantity': self.available_quantity,
            'reserved_quantity': self.reserved_quantity,
            'low_stock_threshold': self.low_stock_threshold,
            'is_low_stock': self.is_low_stock,
            'is_out_of_stock': self.is_out_of_stock
        }

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Sierra Leone')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_utc)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'city': self.city,
            'is_active': self.is_active
        }

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Sierra Leone')
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    loyalty_points = db.Column(db.Integer, default=0)
    customer_tier = db.Column(db.String(20), default='BRONZE')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_utc)
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f"{self.first_name} {self.last_name}",
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'total_orders': self.total_orders,
            'total_spent': self.total_spent,
            'loyalty_points': self.loyalty_points,
            'customer_tier': self.customer_tier
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'))
    customer_email = db.Column(db.String(120))
    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(20))
    shipping_address = db.Column(db.Text)
    shipping_city = db.Column(db.String(100))
    shipping_state = db.Column(db.String(100))
    shipping_country = db.Column(db.String(100), default='Sierra Leone')
    subtotal = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    shipping_cost = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    order_status = db.Column(db.String(20), default='PENDING')
    payment_status = db.Column(db.String(20), default='PENDING')
    order_date = db.Column(db.DateTime, default=now_utc)
    confirmed_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    customer_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_utc)
    
    customer = db.relationship('Customer', backref='orders')
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'customer_email': self.customer_email,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'shipping_address': self.shipping_address,
            'shipping_city': self.shipping_city,
            'shipping_state': self.shipping_state,
            'shipping_country': self.shipping_country,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'shipping_cost': self.shipping_cost,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'customer_notes': self.customer_notes,
            'items': [i.to_dict() for i in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'))
    product_name = db.Column(db.String(300))
    product_sku = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, default=0)
    vendor_id = db.Column(db.String(36), db.ForeignKey('vendors.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'tax_rate': self.tax_rate,
            'total_price': self.total_price,
            'vendor_id': self.vendor_id
        }

# ============ CORS HEADERS ============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# ============ UPLOADS ============
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============ AUTH ROUTES ============
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email', '').lower()).first()
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user.is_active:
        return jsonify({'error': 'Account deactivated'}), 403
    user.last_login = now_utc()
    db.session.commit()
    token = create_token(user.id, user.role, user.email, f"{user.first_name} {user.last_name}")
    return jsonify({'access_token': token, 'user': user.to_dict()}), 200

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400
    if not data.get('first_name'):
        return jsonify({'error': 'First name is required'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data['email'].lower()).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create user
    user = User(
        email=data['email'].lower(),
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        role=data.get('role', 'VENDOR'),
        phone=data.get('phone', '')
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()
    
    # Create vendor profile for the user
    vendor = Vendor(
        user_id=user.id,
        business_name=f"{user.first_name}'s Store",
        business_email=user.email,
        is_verified=True
    )
    db.session.add(vendor)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201

@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile():
    user = User.query.get(request.current_user['user_id'])
    return jsonify(user.to_dict()) if user else (jsonify({'error': 'Not found'}), 404)

# ============ PRODUCT ROUTES ============
@app.route('/api/products/', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    query = Product.query
    
    if request.args.get('status'):
        query = query.filter_by(status=request.args.get('status'))
    if request.args.get('search'):
        search = request.args.get('search')
        query = query.filter(db.or_(
            Product.name.ilike(f"%{search}%"),
            Product.sku.ilike(f"%{search}%")
        ))
    if request.args.get('category'):
        query = query.filter_by(category_id=request.args.get('category'))
    
    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'products': [p.to_dict() for p in products.items],
        'total': products.total,
        'pages': products.pages,
        'current_page': products.page
    })

@app.route('/api/products/<pid>', methods=['GET'])
def get_product(pid):
    p = Product.query.get(pid)
    return jsonify(p.to_dict()) if p else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/products/', methods=['POST'])
@token_required
def create_product():
    if request.is_json:
        data = request.get_json()
        image_path = None
    else:
        data = request.form.to_dict()
        image_path = save_image(request.files.get('main_image'), 'products')
    
    if Product.query.filter_by(sku=data['sku']).first():
        return jsonify({'error': 'SKU exists'}), 409
    
    vendor = Vendor.query.filter_by(user_id=request.current_user['user_id']).first()
    if not vendor:
        vendor = Vendor(
            user_id=request.current_user['user_id'],
            business_name="My Store",
            business_email=request.current_user.get('email', ''),
            is_verified=True
        )
        db.session.add(vendor)
        db.session.flush()
    
    p = Product(
        sku=data['sku'],
        name=data['name'],
        slug=data.get('slug', data['name'].lower().replace(' ', '-')),
        description=data.get('description', ''),
        short_description=data.get('short_description', (data.get('description', '') or '')[:200]),
        cost_price=float(data['cost_price']),
        selling_price=float(data['selling_price']),
        discount_price=float(data['discount_price']) if data.get('discount_price') else None,
        category_id=data.get('category_id'),
        vendor_id=vendor.id,
        main_image=image_path or data.get('main_image'),
        status=data.get('status', 'ACTIVE')
    )
    db.session.add(p)
    db.session.flush()
    inv = Inventory(
        product_id=p.id,
        quantity=int(data.get('quantity', 0)),
        low_stock_threshold=int(data.get('low_stock_threshold', 10))
    )
    db.session.add(inv)
    db.session.commit()
    return jsonify(p.to_dict()), 201

@app.route('/api/products/<pid>', methods=['PUT'])
@token_required
def update_product(pid):
    p = Product.query.get(pid)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    if request.files and request.files.get('main_image'):
        p.main_image = save_image(request.files['main_image'], 'products')
    
    for f in ['name', 'description', 'short_description', 'status']:
        if f in data:
            setattr(p, f, data[f])
    for f in ['cost_price', 'selling_price', 'discount_price']:
        if f in data and data[f] not in [None, '']:
            setattr(p, f, float(data[f]))
    if 'category_id' in data:
        p.category_id = data['category_id']
    if 'main_image' in data and data['main_image']:
        p.main_image = data['main_image']
    
    db.session.commit()
    return jsonify(p.to_dict())

@app.route('/api/products/<pid>', methods=['DELETE'])
@token_required
def delete_product(pid):
    p = Product.query.get(pid)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({'message': 'Product deleted'})

@app.route('/api/products/categories', methods=['GET'])
def get_categories():
    return jsonify([c.to_dict() for c in Category.query.all()])

@app.route('/api/products/categories', methods=['POST'])
@token_required
def create_category():
    data = request.get_json() if request.is_json else request.form.to_dict()
    image_path = save_image(request.files.get('image'), 'categories') if request.files and request.files.get('image') else None
    cat = Category(
        name=data['name'],
        slug=data.get('slug', data['name'].lower().replace(' ', '-')),
        description=data.get('description', ''),
        image=image_path or data.get('image'),
        parent_id=data.get('parent_id')
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201

# ============ ORDER ROUTES ============
@app.route('/api/orders/', methods=['GET', 'POST'])
@token_required
def handle_orders():
    if request.method == 'GET':
        query = Order.query
        if request.args.get('status'):
            query = query.filter_by(order_status=request.args.get('status'))
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 50, type=int),
            error_out=False
        )
        return jsonify({
            'orders': [o.to_dict() for o in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': orders.page
        })
    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({'error': 'Items required'}), 400
        
        items = data['items']
        if not items:
            return jsonify({'error': 'At least one item required'}), 400
        
        subtotal = 0
        tax_amount = 0
        
        order = Order(
            order_number=generate_order_number(),
            customer_email=data.get('customer_email', ''),
            customer_name=data.get('customer_name', ''),
            customer_phone=data.get('customer_phone', ''),
            shipping_address=data.get('shipping_address', ''),
            shipping_city=data.get('shipping_city', ''),
            shipping_state=data.get('shipping_state', ''),
            shipping_country=data.get('shipping_country', 'Sierra Leone'),
            subtotal=0,
            tax_amount=0,
            shipping_cost=float(data.get('shipping_cost', 0)),
            discount_amount=float(data.get('discount_amount', 0)),
            total_amount=0,
            order_status='PENDING',
            payment_status='PAID',
            customer_notes=data.get('customer_notes', '')
        )
        db.session.add(order)
        db.session.flush()
        
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({'error': 'Product not found'}), 404
            
            qty = item['quantity']
            price = product.current_price
            itax = price * 0.15
            itotal = (price * qty) + (itax * qty)
            
            subtotal += price * qty
            tax_amount += itax * qty
            
            oi = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=qty,
                unit_price=price,
                tax_rate=15.0,
                total_price=itotal,
                vendor_id=product.vendor_id
            )
            db.session.add(oi)
        
        order.subtotal = subtotal
        order.tax_amount = tax_amount
        order.total_amount = subtotal + tax_amount + order.shipping_cost - order.discount_amount
        
        customer = Customer.query.filter_by(email=data.get('customer_email', '').lower()).first()
        if customer:
            order.customer_id = customer.id
        
        db.session.commit()
        return jsonify(order.to_dict()), 201

@app.route('/api/orders/<oid>', methods=['GET'])
@token_required
def get_order(oid):
    order = Order.query.get(oid)
    return jsonify(order.to_dict()) if order else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/orders/<oid>/status', methods=['PUT'])
@admin_required
def update_order_status(oid):
    order = Order.query.get(oid)
    if not order:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status required'}), 400
    
    order.order_status = new_status
    
    if new_status == 'CONFIRMED':
        order.confirmed_at = now_utc()
        order.payment_status = 'PAID'
    elif new_status == 'PROCESSING':
        order.payment_status = 'PAID'
    elif new_status == 'SHIPPED':
        order.shipped_at = now_utc()
        order.payment_status = 'PAID'
    elif new_status == 'IN_TRANSIT':
        order.payment_status = 'PAID'
    elif new_status == 'DELIVERED':
        order.delivered_at = now_utc()
        order.payment_status = 'PAID'
        if order.customer:
            order.customer.total_orders = (order.customer.total_orders or 0) + 1
            order.customer.total_spent = (order.customer.total_spent or 0) + order.total_amount
            order.customer.loyalty_points = (order.customer.loyalty_points or 0) + int(order.total_amount / 100)
    elif new_status == 'CANCELLED':
        order.cancelled_at = now_utc()
        order.payment_status = 'CANCELLED'
    
    db.session.commit()
    return jsonify(order.to_dict())

@app.route('/api/orders/<oid>/tracking', methods=['GET'])
@token_required
def get_order_tracking(oid):
    order = Order.query.get(oid)
    if not order:
        return jsonify({'error': 'Not found'}), 404
    
    if order.order_status == 'CANCELLED':
        tracking = [
            {'status': 'Order Placed', 'date': order.order_date.isoformat() if order.order_date else None, 'completed': True, 'icon': 'fa-receipt'},
            {'status': 'Cancelled', 'date': order.cancelled_at.isoformat() if order.cancelled_at else None, 'completed': True, 'icon': 'fa-times-circle', 'color': 'danger'}
        ]
    else:
        tracking = [
            {'status': 'Order Placed', 'date': order.order_date.isoformat() if order.order_date else None, 'completed': True, 'icon': 'fa-receipt'},
            {'status': 'Confirmed', 'date': order.confirmed_at.isoformat() if order.confirmed_at else None, 'completed': order.order_status in ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'IN_TRANSIT', 'DELIVERED'], 'icon': 'fa-check-circle'},
            {'status': 'Processing', 'date': None, 'completed': order.order_status in ['PROCESSING', 'SHIPPED', 'IN_TRANSIT', 'DELIVERED'], 'icon': 'fa-cog'},
            {'status': 'Shipped', 'date': order.shipped_at.isoformat() if order.shipped_at else None, 'completed': order.order_status in ['SHIPPED', 'IN_TRANSIT', 'DELIVERED'], 'icon': 'fa-truck'},
            {'status': 'In Transit', 'date': None, 'completed': order.order_status in ['IN_TRANSIT', 'DELIVERED'], 'icon': 'fa-shipping-fast'},
            {'status': 'Delivered', 'date': order.delivered_at.isoformat() if order.delivered_at else None, 'completed': order.order_status == 'DELIVERED', 'icon': 'fa-box-check'},
        ]
    
    return jsonify({
        'order_number': order.order_number,
        'order_status': order.order_status,
        'tracking': tracking
    })

@app.route('/api/my-orders/', methods=['GET'])
@token_required
def my_orders():
    email = request.current_user.get('email', '')
    orders = Order.query.filter_by(customer_email=email).order_by(Order.created_at.desc()).all()
    return jsonify({'orders': [o.to_dict() for o in orders]})

# ============ CUSTOMER ROUTES ============
@app.route('/api/customers/', methods=['GET'])
@token_required
def get_customers():
    query = Customer.query
    if request.args.get('search'):
        search = request.args.get('search')
        query = query.filter(db.or_(
            Customer.first_name.ilike(f"%{search}%"),
            Customer.last_name.ilike(f"%{search}%"),
            Customer.email.ilike(f"%{search}%")
        ))
    customers = query.order_by(Customer.created_at.desc()).paginate(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 20, type=int),
        error_out=False
    )
    return jsonify({
        'customers': [c.to_dict() for c in customers.items],
        'total': customers.total,
        'pages': customers.pages,
        'current_page': customers.page
    })

# ============ VENDOR ROUTES ============
@app.route('/api/vendors/', methods=['GET'])
@token_required
def get_vendors():
    return jsonify([v.to_dict() for v in Vendor.query.all()])

# ============ INVENTORY ROUTES ============
@app.route('/api/inventory/', methods=['GET'])
@token_required
def get_inventory():
    query = Inventory.query
    if request.args.get('warehouse_id'):
        query = query.filter_by(warehouse_id=request.args.get('warehouse_id'))
    
    inv = query.paginate(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 50, type=int),
        error_out=False
    )
    
    return jsonify({
        'items': [{
            **i.to_dict(),
            'product_name': i.product.name if i.product else None,
            'product_sku': i.product.sku if i.product else None
        } for i in inv.items],
        'total': inv.total,
        'pages': inv.pages,
        'current_page': inv.page
    })

# ============ ANALYTICS ROUTES ============
@app.route('/api/analytics/dashboard', methods=['GET'])
@token_required
def dashboard():
    tp = Product.query.count()
    ap = Product.query.filter_by(status='ACTIVE').count()
    to = Order.query.count()
    po = Order.query.filter_by(order_status='PENDING').count()
    tc = Customer.query.count()
    tv = Vendor.query.count()
    oos = Inventory.query.filter_by(quantity=0).count()
    ls = Inventory.query.filter(
        Inventory.quantity <= Inventory.low_stock_threshold,
        Inventory.quantity > 0
    ).count()
    tr = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.payment_status == 'PAID'
    ).scalar() or 0
    
    return jsonify({'overview': {
        'total_products': tp,
        'active_products': ap,
        'total_orders': to,
        'pending_orders': po,
        'total_customers': tc,
        'total_vendors': tv,
        'out_of_stock': oos,
        'low_stock': ls,
        'total_revenue': float(tr)
    }})

# ============ HEALTH ROUTE ============
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Jumia API Running',
        'version': '5.0',
        'database': 'SQLite'
    })

# ============ SEED ADMIN ============
def seed_admin():
    if User.query.filter_by(email='admin@jumia.com').first():
        return
    
    admin = User(
        email='admin@jumia.com',
        first_name='Admin',
        last_name='User',
        role='ADMIN',
        phone='+23200000000',
        is_verified=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.flush()
    
    vendor = Vendor(
        user_id=admin.id,
        business_name="Jumia Admin Store",
        business_email='admin@jumia.com',
        is_verified=True
    )
    db.session.add(vendor)
    
    wh = Warehouse(name='Main Warehouse', code='WH-001', city='Freetown')
    db.session.add(wh)
    
    db.session.commit()
    print("Admin created: admin@jumia.com / admin123")

# ============ MAIN ============
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_admin()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)