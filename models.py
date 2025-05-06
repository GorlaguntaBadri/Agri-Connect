class Order(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    delivery_info = db.Column(db.JSON)  # Store delivery information as JSON
    items = db.relationship('OrderItem', backref='order', lazy=True)
    coupon_code = db.Column(db.String(20), db.ForeignKey('coupon.code'), nullable=True)
    discount_amount = db.Column(db.Float, default=0.0)

class Coupon(db.Model):
    code = db.Column(db.String(20), primary_key=True)
    discount_percent = db.Column(db.Float, nullable=False)
    min_purchase = db.Column(db.Float, default=0.0)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    usage_limit = db.Column(db.Integer, default=None)
    times_used = db.Column(db.Integer, default=0)
    
    def is_valid(self, total_amount):
        now = datetime.utcnow()
        return (
            self.is_active and
            now >= self.valid_from and
            now <= self.valid_until and
            total_amount >= self.min_purchase and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )
    
    def calculate_discount(self, total_amount):
        return (total_amount * self.discount_percent) / 100 

class ProductAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    views = db.Column(db.Integer, default=0)
    purchases = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    seasonal_demand = db.Column(db.Float, default=0.0)  # 0-1 scale indicating seasonal demand
    price_trend = db.Column(db.Float, default=0.0)  # Price trend over time
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Addagroproducts', backref=db.backref('analytics', uselist=False))

class ProductReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Addagroproducts', backref=db.backref('reviews', lazy=True))
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('shopping_lists', lazy=True))
    items = db.relationship('ShoppingListItem', backref='shopping_list', lazy=True, cascade='all, delete-orphan')

class ShoppingListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shopping_list_id = db.Column(db.Integer, db.ForeignKey('shopping_list.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    notes = db.Column(db.String(200))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Addagroproducts', backref=db.backref('shopping_list_items', lazy=True))

class PriceAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('price_alerts', lazy=True))
    product = db.relationship('Addagroproducts', backref=db.backref('price_alerts', lazy=True)) 