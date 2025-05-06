from flask import Flask,render_template,request,session,redirect,url_for,flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import login_user,logout_user,login_manager,LoginManager
from flask_login import login_required,current_user
from datetime import datetime, timedelta
import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MY db connection
local_server= True
app = Flask(__name__)
app.secret_key='harshithbhaskar'

# Configure Stripe
stripe.api_key = 'sk_test_51RGqz1BAXt6OUPBi1Co8TpzqvkZQw1FzLV8gyvI86Tv5ysX505hnAsoh4aVCtEpLLrhwBYz5RHpJ5tySqB5PgBj800qj3SKHMv'
STRIPE_PUBLISHABLE_KEY = 'pk_test_51RGqz1BAXt6OUPBibM1YSpsuj192gE8oeL9WKloC2WEldcICJ4kZMTUV9xe91AuwJjhkZoqZLEMLesQUmLEVxdYU00rFfMPjlG'

# this is for getting unique user access
login_manager=LoginManager(app)
login_manager.login_view='login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# app.config['SQLALCHEMY_DATABASE_URL']='mysql://username:password@localhost/databas_table_name'
app.config['SQLALCHEMY_DATABASE_URI']='mysql+mysqlconnector://root:@localhost/farmers'
db=SQLAlchemy(app)

# here we will create db models that is tables
class Test(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100))

class Farming(db.Model):
    fid=db.Column(db.Integer,primary_key=True)
    farmingtype=db.Column(db.String(100))


class Addagroproducts(db.Model):
    pid=db.Column(db.Integer,primary_key=True)
    productname=db.Column(db.String(100))
    productdesc=db.Column(db.String(300))
    quantity=db.Column(db.Integer)
    price=db.Column(db.Float, nullable=True)  # Made price nullable
    is_validated=db.Column(db.Boolean, default=False)
    validator_id=db.Column(db.Integer, db.ForeignKey('user.id'))
    farmer_id=db.Column(db.Integer, db.ForeignKey('register.rid'))
    created_at=db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add relationship to Register model
    farmer = db.relationship('Register', backref=db.backref('products', lazy=True))
    validator = db.relationship('User', backref=db.backref('validated_products', lazy=True))

# Add Cart model for buyers
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    product = db.relationship('Addagroproducts', backref=db.backref('cart_items', lazy=True))

# Add Order model for completed purchases
class Order(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True)

# Add OrderItem model for items in an order
class OrderItem(db.Model):
    item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Relationships
    product = db.relationship('Addagroproducts', backref=db.backref('order_items', lazy=True))

class Trig(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    fid=db.Column(db.String(100))
    action=db.Column(db.String(100))
    timestamp=db.Column(db.String(100))


class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50))
    email=db.Column(db.String(50),unique=True)
    password=db.Column(db.String(1000))
    role=db.Column(db.String(20))

class Register(db.Model):
    rid=db.Column(db.Integer,primary_key=True)
    farmername=db.Column(db.String(50))
    adharnumber=db.Column(db.String(50))
    age=db.Column(db.Integer)
    gender=db.Column(db.String(50))
    phonenumber=db.Column(db.String(50))
    address=db.Column(db.String(50))
    farming=db.Column(db.String(50))
    role=db.Column(db.String(20))
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)  # Added unique constraint

    

@app.context_processor
def inject_profile():
    if current_user.is_authenticated:
        profile = Register.query.filter_by(user_id=current_user.id).first()
        return {'profile': profile}
    return {'profile': None}

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/farmerdetails')
@login_required
def farmerdetails():
    query=Register.query.all()
    return render_template('farmerdetails.html',query=query)

@app.route('/agroproducts')
def agroproducts():
    # Only show validated products
    query = Addagroproducts.query.filter_by(is_validated=True).all()
    return render_template('agroproducts.html', products=query)

@app.route('/addagroproduct',methods=['POST','GET'])
@login_required
def addagroproduct():
    # Check if user is a farmer
    if current_user.role != 'farmer':
        flash("Only farmers can add products", "warning")
        return redirect('/')
        
    # Get farmer profile
    farmer_profile = Register.query.filter_by(user_id=current_user.id).first()
    if not farmer_profile:
        flash("Please create your farmer profile first", "warning")
        return redirect('/farmerprofile')
        
    if request.method=="POST":
        try:
            productname = request.form.get('productname')
            productdesc = request.form.get('productdesc')
            quantity = request.form.get('quantity', type=int)
            
            # Validate input
            if not productname or not productdesc:
                flash("Please fill in all fields", "warning")
                return redirect('/addagroproduct')
                
            if not quantity or quantity < 1:
                flash("Please enter a valid quantity", "warning")
                return redirect('/addagroproduct')
            
            print(f"Adding product: {productname}, Quantity: {quantity}, Farmer ID: {farmer_profile.rid}")
            
            # Create new product
            product = Addagroproducts(
                productname=productname,
                productdesc=productdesc,
                quantity=quantity,
                farmer_id=farmer_profile.rid,
                price=0.0,  # Set default price to 0.0 instead of None
                is_validated=False
            )
            
            print("Product object created, adding to session...")
            db.session.add(product)
            print("Committing to database...")
            db.session.commit()
            print("Product added successfully!")
            
            flash("Product Added Successfully. It will be available after validation.", "success")
            return redirect('/myproducts')
            
        except Exception as e:
            print(f"Error adding product: {str(e)}")
            db.session.rollback()
            flash(f"Error adding product: {str(e)}", "warning")
            return redirect('/addagroproduct')
   
    return render_template('addagroproducts.html')

@app.route('/myproducts')
@login_required
def myproducts():
    # Check if user is a farmer
    if current_user.role != 'farmer':
        flash("Only farmers can view their products", "warning")
        return redirect('/')
        
    # Get farmer profile
    farmer_profile = Register.query.filter_by(user_id=current_user.id).first()
    if not farmer_profile:
        flash("Please create your farmer profile first", "warning")
        return redirect('/farmerprofile')
        
    # Get farmer's products
    products = Addagroproducts.query.filter_by(farmer_id=farmer_profile.rid).all()
    return render_template('myproducts.html', products=products)

@app.route('/triggers')
@login_required
def triggers():
    query=Trig.query.all()
    return render_template('triggers.html',query=query)

@app.route('/addfarming',methods=['POST','GET'])
@login_required
def addfarming():
    if request.method=="POST":
        farmingtype=request.form.get('farming')
        query=Farming.query.filter_by(farmingtype=farmingtype).first()
        if query:
            flash("Farming Type Already Exist","warning")
            return redirect('/addfarming')
        dep=Farming(farmingtype=farmingtype)
        db.session.add(dep)
        db.session.commit()
        flash("Farming Addes","success")
    return render_template('farming.html')

@app.route("/delete/<string:rid>",methods=['POST','GET'])
@login_required
def delete(rid):
    post=Register.query.filter_by(rid=rid).first()
    db.session.delete(post)
    db.session.commit()
    flash("Slot Deleted Successful","warning")
    return redirect('/farmerdetails')

@app.route("/edit/<string:rid>",methods=['POST','GET'])
@login_required
def edit(rid):
    if request.method=="POST":
        # Check if the profile belongs to the current user
        post = Register.query.filter_by(rid=rid).first()
        if post.user_id != current_user.id:
            flash("You can only edit your own profile", "warning")
            return redirect('/')
            
        farmername=request.form.get('farmername')
        adharnumber=request.form.get('adharnumber')
        age=request.form.get('age')
        gender=request.form.get('gender')
        phonenumber=request.form.get('phonenumber')
        address=request.form.get('address')
        farmingtype=request.form.get('farmingtype')
        role=request.form.get('role')
        
        post.farmername=farmername
        post.adharnumber=adharnumber
        post.age=age
        post.gender=gender
        post.phonenumber=phonenumber
        post.address=address
        post.farming=farmingtype
        post.role=role
        db.session.commit()
        flash("Profile Updated Successfully", "success")
        return redirect('/')
        
    # Check if the profile belongs to the current user
    post = Register.query.filter_by(rid=rid).first()
    if post.user_id != current_user.id:
        flash("You can only edit your own profile", "warning")
        return redirect('/')
        
    farming=Farming.query.all()
    return render_template('edit.html',posts=post,farming=farming)

@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method == "POST":
        username=request.form.get('username')
        email=request.form.get('email')
        password=request.form.get('password')
        role=request.form.get('role')
        user=User.query.filter_by(email=email).first()
        if user:
            flash("Email Already Exists","warning")
            return render_template('signup.html')
        new_user=User(username=username,email=email,password=password,role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Signup Success Please Login","success")
        return render_template('login.html')

    return render_template('signup.html')

@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "POST":
        email=request.form.get('email')
        password=request.form.get('password')
        user=User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            flash("Login Success","primary")
            return redirect(url_for('index'))
        else:
            flash("invalid credentials","warning")
            return render_template('login.html')    

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout SuccessFul","warning")
    return redirect(url_for('login'))

@app.route('/register',methods=['POST','GET'])
@login_required
def register():
    # Check if user already has a profile
    existing_profile = Register.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash("You can only create one profile. Please use the edit option to modify your existing profile.", "warning")
        return redirect('/')
        
    farming=Farming.query.all()
    if request.method=="POST":
        farmername=request.form.get('farmername')
        adharnumber=request.form.get('adharnumber')
        age=request.form.get('age')
        gender=request.form.get('gender')
        phonenumber=request.form.get('phonenumber')
        address=request.form.get('address')
        farmingtype=request.form.get('farmingtype')
        role=request.form.get('role')
        
        # Check if Aadhar number already exists
        existing_aadhar = Register.query.filter_by(adharnumber=adharnumber).first()
        if existing_aadhar:
            flash("A profile with this Aadhar number already exists", "warning")
            return redirect('/register')
            
        query=Register(
            farmername=farmername,
            adharnumber=adharnumber,
            age=age,
            gender=gender,
            phonenumber=phonenumber,
            address=address,
            farming=farmingtype,
            role=role,
            user_id=current_user.id
        )
        try:
            db.session.add(query)
            db.session.commit()
            flash("Profile created successfully", "success")
            return redirect('/farmerdetails')
        except Exception as e:
            db.session.rollback()
            flash("Error creating profile. Please try again.", "warning")
            return redirect('/register')
            
    return render_template('farmer.html',farming=farming)

@app.route('/farmerprofile',methods=['POST','GET'])
@login_required
def farmerprofile():
    farming=Farming.query.all()
    
    # Check if user already has a profile
    existing_profile = Register.query.filter_by(user_id=current_user.id).first()
    
    if request.method=="POST":
        # If user already has a profile, redirect to edit
        if existing_profile:
            flash("You already have a profile. Please use the edit option.", "warning")
            return redirect('/')
            
        farmername=request.form.get('farmername')
        adharnumber=request.form.get('adharnumber')
        age=request.form.get('age')
        gender=request.form.get('gender')
        phonenumber=request.form.get('phonenumber')
        address=request.form.get('address')
        farmingtype=request.form.get('farmingtype')
        role=request.form.get('role')
        
        # Check if farmer already exists with this Aadhar
        existing_farmer = Register.query.filter_by(adharnumber=adharnumber).first()
        if existing_farmer:
            flash("Farmer with this Aadhar number already exists", "warning")
            return redirect('/farmerprofile')
            
        # Create new farmer profile
        new_farmer = Register(
            farmername=farmername,
            adharnumber=adharnumber,
            age=age,
            gender=gender,
            phonenumber=phonenumber,
            address=address,
            farming=farmingtype,
            role=role,
            user_id=current_user.id  # Link to current user
        )
        db.session.add(new_farmer)
        db.session.commit()
        flash("Farmer profile created successfully", "success")
        return redirect('/')
        
    # If user already has a profile, redirect to edit
    if existing_profile:
        return redirect(url_for('edit', rid=existing_profile.rid))
        
    return render_template('farmerprofile.html', farming=farming)

@app.route('/test')
def test():
    try:
        Test.query.all()
        return 'My database is Connected'
    except:
        return 'My db is not Connected'

@app.route('/validate_product/<int:pid>', methods=['GET', 'POST'])
@login_required
def validate_product(pid):
    # Check if user is a validator
    if current_user.role != 'validator':
        flash("Only validators can validate products", "warning")
        return redirect('/')
        
    # Get the product
    product = Addagroproducts.query.get_or_404(pid)
    
    if request.method == "POST":
        # Get validation data
        price = request.form.get('price')
        
        # Update product
        product.price = float(price)
        product.is_validated = True
        product.validator_id = current_user.id
        
        db.session.commit()
        flash("Product validated successfully", "success")
        return redirect('/agroproducts')
        
    return render_template('validate_product.html', product=product)

@app.route('/pending_products')
@login_required
def pending_products():
    # Check if user is a validator
    if current_user.role != 'validator':
        flash("Only validators can view pending products", "warning")
        return redirect('/')
        
    # Get unvalidated products
    products = Addagroproducts.query.filter_by(is_validated=False).all()
    return render_template('pending_products.html', products=products)

@app.route('/add_to_cart/<int:pid>', methods=['POST'])
@login_required
def add_to_cart(pid):
    if current_user.role != 'buyer':
        flash('Only buyers can add products to cart', 'error')
        return redirect(url_for('agroproducts'))
    
    product = Addagroproducts.query.get_or_404(pid)
    if not product.is_validated:
        flash('This product is not available for purchase yet', 'error')
        return redirect(url_for('agroproducts'))
    
    quantity = request.form.get('quantity', type=int)
    if not quantity or quantity < 1:
        flash('Please enter a valid quantity', 'error')
        return redirect(url_for('agroproducts'))
    
    # Check if requested quantity exceeds available quantity
    if quantity > product.quantity:
        flash(f'Only {product.quantity} items available. Please select a lower quantity.', 'error')
        return redirect(url_for('agroproducts'))
    
    # Check if product already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=pid).first()
    if cart_item:
        # Check if total quantity (existing + new) exceeds available quantity
        if cart_item.quantity + quantity > product.quantity:
            flash(f'Only {product.quantity} items available. You already have {cart_item.quantity} in your cart.', 'error')
            return redirect(url_for('agroproducts'))
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=pid, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'Added {quantity} {product.productname}(s) to cart', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    if current_user.role != 'buyer':
        flash('Only buyers can access the cart', 'warning')
        return redirect(url_for('agroproducts'))
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total_items = sum(item.quantity for item in cart_items)
    total_amount = sum(item.quantity * item.product.price for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total_items=total_items, total_amount=total_amount)

@app.route('/update_cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can update cart'}), 403
    
    cart_item = Cart.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not cart_item:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404
    
    data = request.get_json()
    new_quantity = data.get('quantity', 0)
    
    if new_quantity < 1:
        return jsonify({'success': False, 'message': 'Quantity cannot be less than 1'}), 400
        
    # Check if new quantity exceeds available product quantity
    if new_quantity > cart_item.product.quantity:
        return jsonify({
            'success': False, 
            'message': f'Only {cart_item.product.quantity} items available'
        }), 400
    
    cart_item.quantity = new_quantity
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can remove from cart'}), 403
    
    cart_item = Cart.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not cart_item:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404
    
    db.session.delete(cart_item)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/checkout')
@login_required
def checkout():
    if current_user.role != 'buyer':
        flash('Only buyers can checkout', 'warning')
        return redirect(url_for('agroproducts'))
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    total_amount = sum(item.quantity * item.product.price for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount)

@app.route('/validate_coupon', methods=['POST'])
@login_required
def validate_coupon():
    if current_user.role != 'buyer':
        return jsonify({'success': False, 'message': 'Only buyers can use coupons'}), 403
    
    data = request.get_json()
    coupon_code = data.get('coupon_code')
    total_amount = data.get('total_amount', 0)
    
    if not coupon_code:
        return jsonify({'success': False, 'message': 'Please enter a coupon code'}), 400
    
    coupon = Coupon.query.get(coupon_code)
    if not coupon:
        return jsonify({'success': False, 'message': 'Invalid coupon code'}), 400
    
    if not coupon.is_valid(total_amount):
        if not coupon.is_active:
            message = 'This coupon is no longer active'
        elif datetime.utcnow() < coupon.valid_from:
            message = 'This coupon is not yet valid'
        elif datetime.utcnow() > coupon.valid_until:
            message = 'This coupon has expired'
        elif total_amount < coupon.min_purchase:
            message = f'Minimum purchase amount of ₹{coupon.min_purchase} required'
        else:
            message = 'This coupon has reached its usage limit'
        return jsonify({'success': False, 'message': message}), 400
    
    discount_amount = coupon.calculate_discount(total_amount)
    return jsonify({
        'success': True,
        'coupon': {
            'code': coupon.code,
            'discount_percent': coupon.discount_percent
        },
        'discount_amount': discount_amount
    })

@app.route('/process_checkout', methods=['POST'])
@login_required
def process_checkout():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can checkout'}), 403
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({'error': 'Your cart is empty'}), 400
    
    # Get delivery information from request
    data = request.get_json()
    required_fields = ['full_name', 'phone', 'address', 'city', 'state', 'pincode']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Please fill in all required fields'}), 400
    
    # Store delivery information in session
    session['delivery_info'] = {
        'full_name': data['full_name'],
        'phone': data['phone'],
        'address': data['address'],
        'city': data['city'],
        'state': data['state'],
        'pincode': data['pincode']
    }
    
    # Calculate total amount
    total_amount = sum(item.quantity * item.product.price for item in cart_items)
    
    # Apply coupon if provided
    discount_amount = 0
    if data.get('coupon_code'):
        coupon = Coupon.query.get(data['coupon_code'])
        if coupon and coupon.is_valid(total_amount):
            discount_amount = coupon.calculate_discount(total_amount)
            total_amount -= discount_amount
            # Increment coupon usage
            coupon.times_used += 1
            db.session.commit()
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(total_amount * 100),  # Amount in paise
                    'product_data': {
                        'name': 'Farm Products Order',
                        'description': f'Order for {len(cart_items)} items',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', _external=True),
            cancel_url=url_for('payment_cancel', _external=True),
            metadata={
                'user_id': current_user.id,
                'order_total': total_amount,
                'item_count': len(cart_items),
                'coupon_code': data.get('coupon_code'),
                'discount_amount': discount_amount
            }
        )
        
        # Store session ID in user session for later verification
        session['checkout_session_id'] = checkout_session.id
        
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 403

@app.route('/payment_success')
@login_required
def payment_success():
    # Verify the payment was successful
    checkout_session_id = session.get('checkout_session_id')
    if not checkout_session_id:
        flash('Payment verification failed', 'error')
        return redirect(url_for('cart'))
    
    try:
        checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
        
        # Get cart items
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        
        # Get delivery information from session
        delivery_info = session.get('delivery_info')
        if not delivery_info:
            flash('Delivery information not found', 'error')
            return redirect(url_for('cart'))
        
        # Create order
        order = Order(
            user_id=current_user.id,
            total_amount=sum(item.quantity * item.product.price for item in cart_items),
            status='Completed',
            delivery_info=delivery_info,
            coupon_code=checkout_session.metadata.get('coupon_code'),
            discount_amount=float(checkout_session.metadata.get('discount_amount', 0))
        )
        db.session.add(order)
        db.session.flush()  # Get the order_id without committing
        
        # Create order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)
            
            # Update product quantity
            item.product.quantity -= item.quantity
        
        # Clear the cart
        for item in cart_items:
            db.session.delete(item)
        
        db.session.commit()
        
        # Clear the session
        session.pop('checkout_session_id', None)
        session.pop('delivery_info', None)
        
        flash('Payment successful! Your order has been placed.', 'success')
        return redirect(url_for('orders'))
    except Exception as e:
        flash(f'Error verifying payment: {str(e)}', 'error')
        return redirect(url_for('cart'))

@app.route('/payment_cancel')
@login_required
def payment_cancel():
    flash('Payment was cancelled', 'warning')
    return redirect(url_for('cart'))

@app.route('/orders')
@login_required
def orders():
    # Check if user is a buyer
    if current_user.role != 'buyer':
        flash("Only buyers can view orders", "warning")
        return redirect('/agroproducts')
    
    # Get current orders (orders from last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    current_orders = Order.query.filter_by(user_id=current_user.id)\
        .filter(Order.created_at >= thirty_days_ago)\
        .order_by(Order.created_at.desc()).all()
    
    # Get past orders (orders older than 30 days)
    past_orders = Order.query.filter_by(user_id=current_user.id)\
        .filter(Order.created_at < thirty_days_ago)\
        .order_by(Order.created_at.desc()).all()
    
    return render_template('orders.html', current_orders=current_orders, past_orders=past_orders)

@app.route('/get_ads', methods=['GET'])
def get_ads():
    # Example ads data
    ads = [
        {
            'title': 'Organic Fertilizers',
            'description': 'Boost your crop yield with our organic fertilizers.',
            'link': 'https://example.com/organic-fertilizers'
        },
        {
            'title': 'Tractor Rentals',
            'description': 'Affordable tractor rentals for your farming needs.',
            'link': 'https://example.com/tractor-rentals'
        },
        {
            'title': 'Irrigation Systems',
            'description': 'Efficient irrigation systems to save water and increase productivity.',
            'link': 'https://example.com/irrigation-systems'
        }
    ]
    return jsonify(ads)

@app.route('/create_sample_coupons')
@login_required
def create_sample_coupons():
    # Only allow admin/validator to create coupons
    if current_user.role not in ['admin', 'validator']:
        flash('You are not authorized to create coupons', 'error')
        return redirect(url_for('index'))
    
    try:
        # Create sample coupons
        sample_coupons = [
            {
                'code': 'WELCOME10',
                'discount_percent': 10.0,
                'min_purchase': 500.0,
                'valid_from': datetime.utcnow(),
                'valid_until': datetime.utcnow() + timedelta(days=30),
                'is_active': True,
                'usage_limit': 100
            },
            {
                'code': 'SUMMER20',
                'discount_percent': 20.0,
                'min_purchase': 1000.0,
                'valid_from': datetime.utcnow(),
                'valid_until': datetime.utcnow() + timedelta(days=60),
                'is_active': True,
                'usage_limit': 50
            },
            {
                'code': 'FARMER15',
                'discount_percent': 15.0,
                'min_purchase': 750.0,
                'valid_from': datetime.utcnow(),
                'valid_until': datetime.utcnow() + timedelta(days=90),
                'is_active': True,
                'usage_limit': 200
            },
            {
                'code': 'FIRST50',
                'discount_percent': 50.0,
                'min_purchase': 2000.0,
                'valid_from': datetime.utcnow(),
                'valid_until': datetime.utcnow() + timedelta(days=15),
                'is_active': True,
                'usage_limit': 10
            },
            {
                'code': 'REGULAR5',
                'discount_percent': 5.0,
                'min_purchase': 0.0,
                'valid_from': datetime.utcnow(),
                'valid_until': datetime.utcnow() + timedelta(days=365),
                'is_active': True,
                'usage_limit': None  # Unlimited usage
            }
        ]
        
        for coupon_data in sample_coupons:
            # Check if coupon already exists
            existing_coupon = Coupon.query.get(coupon_data['code'])
            if not existing_coupon:
                coupon = Coupon(**coupon_data)
                db.session.add(coupon)
        
        db.session.commit()
        flash('Sample coupons created successfully!', 'success')
        
        # Display coupon information
        coupons = Coupon.query.all()
        return render_template('coupons.html', coupons=coupons)
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating sample coupons: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/coupons')
@login_required
def view_coupons():
    if current_user.role not in ['admin', 'validator']:
        flash('You are not authorized to view coupons', 'error')
        return redirect(url_for('index'))
    
    coupons = Coupon.query.all()
    return render_template('coupons.html', coupons=coupons)

@app.route('/product/<int:pid>')
def product_details(pid):
    product = Addagroproducts.query.get_or_404(pid)
    
    # Update view count
    analytics = product.analytics or ProductAnalytics(product_id=pid)
    analytics.views += 1
    analytics.last_updated = datetime.utcnow()
    db.session.add(analytics)
    db.session.commit()
    
    # Get similar products
    similar_products = Addagroproducts.query.filter(
        Addagroproducts.pid != pid,
        Addagroproducts.is_validated == True
    ).limit(4).all()
    
    # Get reviews
    reviews = ProductReview.query.filter_by(product_id=pid).order_by(ProductReview.created_at.desc()).all()
    
    # Calculate seasonal demand (example: higher in summer for certain products)
    current_month = datetime.utcnow().month
    seasonal_products = {
        'summer': [6, 7, 8],  # June, July, August
        'winter': [12, 1, 2],  # December, January, February
        'monsoon': [7, 8, 9],  # July, August, September
    }
    
    seasonal_demand = 0.5  # Default neutral demand
    for season, months in seasonal_products.items():
        if current_month in months:
            # Example seasonal adjustments
            if season == 'summer' and 'fruit' in product.productname.lower():
                seasonal_demand = 0.8
            elif season == 'winter' and 'vegetable' in product.productname.lower():
                seasonal_demand = 0.7
    
    analytics.seasonal_demand = seasonal_demand
    db.session.commit()
    
    return render_template('product_details.html', 
                         product=product, 
                         similar_products=similar_products,
                         reviews=reviews,
                         seasonal_demand=seasonal_demand)

@app.route('/add_review/<int:pid>', methods=['POST'])
@login_required
def add_review(pid):
    if current_user.role != 'buyer':
        flash('Only buyers can leave reviews', 'error')
        return redirect(url_for('product_details', pid=pid))
    
    rating = request.form.get('rating', type=int)
    review_text = request.form.get('review_text')
    
    if not rating or rating < 1 or rating > 5:
        flash('Please provide a valid rating', 'error')
        return redirect(url_for('product_details', pid=pid))
    
    # Check if user has purchased the product
    has_purchased = OrderItem.query.join(Order).filter(
        OrderItem.product_id == pid,
        Order.user_id == current_user.id,
        Order.status == 'Completed'
    ).first()
    
    if not has_purchased:
        flash('You can only review products you have purchased', 'error')
        return redirect(url_for('product_details', pid=pid))
    
    # Check if user has already reviewed
    existing_review = ProductReview.query.filter_by(
        product_id=pid,
        user_id=current_user.id
    ).first()
    
    if existing_review:
        flash('You have already reviewed this product', 'error')
        return redirect(url_for('product_details', pid=pid))
    
    review = ProductReview(
        product_id=pid,
        user_id=current_user.id,
        rating=rating,
        review_text=review_text
    )
    
    db.session.add(review)
    
    # Update product analytics
    analytics = product.analytics or ProductAnalytics(product_id=pid)
    analytics.total_ratings += 1
    analytics.average_rating = (
        (analytics.average_rating * (analytics.total_ratings - 1) + rating) / 
        analytics.total_ratings
    )
    
    db.session.commit()
    flash('Review added successfully', 'success')
    return redirect(url_for('product_details', pid=pid))

@app.route('/shopping_lists')
@login_required
def shopping_lists():
    if current_user.role != 'buyer':
        flash('Only buyers can create shopping lists', 'error')
        return redirect(url_for('index'))
    
    lists = ShoppingList.query.filter_by(user_id=current_user.id).all()
    return render_template('shopping_lists.html', lists=lists)

@app.route('/create_shopping_list', methods=['POST'])
@login_required
def create_shopping_list():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can create shopping lists'}), 403
    
    name = request.form.get('name')
    is_public = request.form.get('is_public') == 'true'
    
    if not name:
        return jsonify({'error': 'Please provide a name for the list'}), 400
    
    shopping_list = ShoppingList(
        user_id=current_user.id,
        name=name,
        is_public=is_public
    )
    
    db.session.add(shopping_list)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'list_id': shopping_list.id,
        'name': shopping_list.name
    })

@app.route('/add_to_shopping_list/<int:list_id>/<int:pid>', methods=['POST'])
@login_required
def add_to_shopping_list(list_id, pid):
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can add to shopping lists'}), 403
    
    shopping_list = ShoppingList.query.get_or_404(list_id)
    if shopping_list.user_id != current_user.id:
        return jsonify({'error': 'You can only add to your own lists'}), 403
    
    quantity = request.form.get('quantity', type=int, default=1)
    notes = request.form.get('notes', '')
    
    item = ShoppingListItem(
        shopping_list_id=list_id,
        product_id=pid,
        quantity=quantity,
        notes=notes
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/set_price_alert/<int:pid>', methods=['POST'])
@login_required
def set_price_alert(pid):
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can set price alerts'}), 403
    
    target_price = request.form.get('target_price', type=float)
    if not target_price or target_price <= 0:
        return jsonify({'error': 'Please provide a valid target price'}), 400
    
    product = Addagroproducts.query.get_or_404(pid)
    
    # Check if alert already exists
    existing_alert = PriceAlert.query.filter_by(
        user_id=current_user.id,
        product_id=pid,
        is_active=True
    ).first()
    
    if existing_alert:
        existing_alert.target_price = target_price
    else:
        alert = PriceAlert(
            user_id=current_user.id,
            product_id=pid,
            target_price=target_price
        )
        db.session.add(alert)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/check_price_alerts')
def check_price_alerts():
    """Background task to check price alerts (should be run periodically)"""
    active_alerts = PriceAlert.query.filter_by(is_active=True).all()
    notifications = []
    
    for alert in active_alerts:
        product = alert.product
        if product.price <= alert.target_price:
            # Create notification
            notification = {
                'user_id': alert.user_id,
                'message': f'Price alert: {product.productname} is now available at ₹{product.price}',
                'product_id': product.pid
            }
            notifications.append(notification)
            
            # Deactivate alert
            alert.is_active = False
    
    db.session.commit()
    return jsonify({'notifications': notifications})

@app.route('/product_recommendations')
@login_required
def product_recommendations():
    if current_user.role != 'buyer':
        flash('Only buyers can view recommendations', 'error')
        return redirect(url_for('index'))
    
    # Get user's purchase history
    purchased_products = OrderItem.query.join(Order).filter(
        Order.user_id == current_user.id,
        Order.status == 'Completed'
    ).all()
    
    # Get products with high ratings and seasonal demand
    recommended_products = Addagroproducts.query.join(ProductAnalytics).filter(
        Addagroproducts.is_validated == True,
        ProductAnalytics.average_rating >= 4.0,
        ProductAnalytics.seasonal_demand >= 0.7
    ).limit(6).all()
    
    return render_template('recommendations.html', 
                         recommended_products=recommended_products,
                         purchased_products=purchased_products)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
