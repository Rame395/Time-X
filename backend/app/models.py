from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Date, UniqueConstraint, LargeBinary
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)   # "men" / "women"
    name = Column(String(50), nullable=False)                # "Men" / "Women"

    products = relationship("Product", back_populates="category")


class Department(Base):
    """Admin-manageable Category/Department values (Clothing, Shoes, Accessories,
    Sports, ...). Kept as a lookup table for validation + populating dropdowns —
    Product.department stays a plain string column, so this needs no migration."""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)   # "shoes"
    name = Column(String(50), nullable=False)                # "Shoes"


class Brand(Base):
    """Watch brands (Titan, Rado, Seiko, or your own house brand) — admin-managed
    so the Brand filter and product form always reflect what you actually sell."""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    slug = Column(String(60), unique=True, nullable=False)
    name = Column(String(80), nullable=False)
    logo_url = Column(String(500), nullable=True)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    slug = Column(String(140), unique=True, nullable=False, index=True)
    title = Column(String(120), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)  # this is GENDER (men/women/unisex)
    department = Column(String(30), default="Classic")   # Automatic | Chronograph | Classic | Diver | Smart — the movement/style category
    subcategory = Column(String(60), default="")             # Heritage, Racing, Skeleton...
    price = Column(Integer, nullable=False)                  # NPR, whole rupees — the current selling price
    compare_at_price = Column(Integer, nullable=True)        # optional "was" price; sale is shown when this > price
    description = Column(Text, default="")
    material = Column(String(200), default="")
    collection_tag = Column(String(60), default="")          # e.g. "limited-edition", "new-arrivals", "best-sellers"
    is_new_arrival = Column(Boolean, default=False)
    is_best_seller = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_limited_edition = Column(Boolean, default=False)
    display_rank = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Watch-specific identity & specs ---
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    model_name = Column(String(120), default="")
    reference_number = Column(String(80), default="")
    sku = Column(String(60), default="", index=True)
    movement = Column(String(40), default="")            # Automatic, Quartz, Chronograph, Smart
    case_material = Column(String(60), default="")       # Stainless Steel, Titanium, Ceramic
    dial_color = Column(String(40), default="")
    strap_material = Column(String(60), default="")      # Leather, Steel Bracelet, Rubber, NATO
    water_resistance = Column(String(20), default="")     # e.g. "50m", "300m"
    glass_type = Column(String(40), default="")           # Mineral, Sapphire Crystal
    warranty = Column(String(40), default="")             # e.g. "2 Years"
    condition = Column(String(20), default="new")         # new | pre-owned
    has_certificate = Column(Boolean, default=False)      # authenticity certificate included
    video_url = Column(String(500), nullable=True)        # optional product demo video

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand")
    images = relationship(
        "ProductImage", back_populates="product",
        cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )
    colors = relationship("ProductColor", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


PRODUCT_IMAGE_ANGLES = ["front", "back", "side", "wrist", "box", "zoom"]


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    color_name = Column(String(50), nullable=True)   # optional — ties a photo to one color's swatch
    angle = Column(String(20), nullable=True)          # front|back|side|wrist|box|zoom — optional shot-type tag

    product = relationship("Product", back_populates="images")


class ProductColor(Base):
    __tablename__ = "product_colors"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(50), nullable=False)
    hex_code = Column(String(7), default="#111111")

    product = relationship("Product", back_populates="colors")


class ProductVariant(Base):
    """A purchasable dial/strap/size combination. `size` holds the case diameter
    (e.g. "40mm") — kept as the historical column name so the cart/order code
    that already keys off size+color needs no migration."""
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "size", "color_name", "strap_material", name="uix_variant"),)

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size = Column(String(10), nullable=False)          # case diameter, e.g. "40mm"
    color_name = Column(String(50), default="")         # dial color's matching ProductColor.name
    strap_material = Column(String(60), default="")     # optional second variant dimension — Leather, Steel, Rubber
    sku = Column(String(60), default="")
    stock_qty = Column(Integer, default=0)
    image_url = Column(String(500), nullable=True)       # optional variant-specific photo (overrides the color-tagged product image)

    product = relationship("Product", back_populates="variants")


class StockHistoryEntry(Base):
    """Audit trail for inventory changes — admin adjustments, order deductions,
    returns, and damaged stock, so admin can see exactly how a number was reached."""
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    change = Column(Integer, nullable=False)             # positive or negative
    reason = Column(String(30), nullable=False)           # order | return | damaged | manual_adjustment | restock
    note = Column(String(200), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    variant = relationship("ProductVariant")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    color = Column(String(50), default="")
    size = Column(String(10), default="")
    strap_material = Column(String(60), default="")
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")


ORDER_STATUSES = [
    "pending", "confirmed", "processing", "packed", "shipped",
    "out_for_delivery", "delivered", "cancelled", "returned", "refunded", "failed",
]


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)

    first_name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(300), nullable=False)
    city = Column(String(80), nullable=False)          # holds the District (Nepal admin structure)
    province = Column(String(50), nullable=False, default="")
    postal_code = Column(String(20), default="")
    landmark = Column(String(200), default="")
    delivery_instructions = Column(String(300), default="")

    payment_method = Column(String(20), nullable=False)      # cod | mobile_banking | esewa | khalti | fonepay | connectips | bank_transfer | whatsapp
    payment_reference = Column(String(200), default="")
    payment_proof_path = Column(String(300), default="")

    status = Column(String(20), default="pending")           # see ORDER_STATUSES
    warranty_status = Column(String(20), default="active")   # active | claimed | void | expired — admin-managed, shown to customer
    coupon_code = Column(String(30), nullable=True)
    discount_amount = Column(Integer, default=0)
    delivery_zone = Column(String(60), default="")
    subtotal = Column(Integer, nullable=False)
    shipping_fee = Column(Integer, default=0)
    total = Column(Integer, nullable=False)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    product_title = Column(String(120), nullable=False)
    color = Column(String(50), default="")
    color_hex = Column(String(7), default="")
    size = Column(String(10), default="")
    strap_material = Column(String(60), default="")
    sku = Column(String(60), default="")
    unit_price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class SiteSetting(Base):
    __tablename__ = "site_settings"

    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")


class Expense(Base):
    """
    Manually-logged business expenses (rent, wages, inventory purchases, etc).
    Income is NOT a mirrored table here — it's derived live from Order totals
    (excluding cancelled orders), since that data already exists and shouldn't
    be duplicated/kept in sync by hand. is_recurring is a plain label for the
    admin's own reference — it does not auto-generate future entries.
    """
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    category = Column(String(30), nullable=False)
    amount = Column(Integer, nullable=False)          # NPR
    note = Column(String(300), default="")
    expense_date = Column(Date, nullable=False)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    """Customer product reviews. order_id links a review to the specific order that
    contained the product, so we can mark it 'Verified Purchase' — nullable because
    we still allow a review without one rather than blocking feedback entirely."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    customer_name = Column(String(100), nullable=False)
    rating = Column(Integer, nullable=False)   # 1-5
    comment = Column(Text, default="")
    is_visible = Column(Boolean, default=True)   # admin can hide/approve without deleting
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")
    photos = relationship("ReviewPhoto", back_populates="review", cascade="all, delete-orphan")


class ReviewPhoto(Base):
    __tablename__ = "review_photos"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    url = Column(String(500), nullable=False)

    review = relationship("Review", back_populates="photos")


RETURN_STATUSES = ["requested", "approved", "rejected", "received", "refunded"]


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="requested")
    admin_note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order = relationship("Order")


SITE_IMAGE_SLOTS = {
    # slot key: (display label, "single" one active image | "multi" any number, page)
    "homepage_hero": ("Homepage — Hero Banner (rotates)", "multi", "index.html"),
    "homepage_hero_video": ("Homepage — Hero Video (plays on hover/touch)", "single", "index.html"),
    "homepage_story": ("Homepage — Editorial Story Section", "single", "index.html"),
    "homepage_tile_men": ("Homepage — Men Tile", "single", "index.html"),
    "homepage_tile_women": ("Homepage — Women Tile", "single", "index.html"),
    "homepage_tile_new": ("Homepage — New Arrivals Tile", "single", "index.html"),
    "instagram_grid": ("Homepage — Instagram Grid", "multi", "index.html"),
    "men_hero": ("Men Page — Hero Banner", "single", "men.html"),
    "women_hero": ("Women Page — Hero Banner", "single", "women.html"),
    "collections_hero": ("Collections — Hero Banner", "single", "collections.html"),
    "blog_hero": ("Blog — Hero Banner", "single", "blog.html"),
    "blog_posts": ("Blog — Journal Entries (add as many as you like)", "multi", "blog.html"),
    "gallery_hero": ("Gallery — Hero Banner", "single", "gallery.html"),
    "gallery_grid": ("Gallery — Editorial Grid", "multi", "gallery.html"),
}

# Slots that expect a video upload (mp4) rather than a photo — the admin form
# and validation both check this.
VIDEO_SLOTS = {"homepage_hero_video"}

# gallery_grid photos are tagged with one of these so they participate in
# gallery.html's existing filter buttons (slug: display label).
GALLERY_CATEGORIES = {
    "studio": "Studio Product Shoot",
    "editorial": "On The Wrist",
    "details": "Movement & Craft",
}

# The 4 categories TIME-X ships with. Distinguishes "original" departments (fixed
# clothing/shoe size sets apply) from anything admin adds later (free-text sizing).
DEFAULT_DEPARTMENTS = [("clothing", "Clothing"), ("shoes", "Shoes"), ("accessories", "Accessories"), ("sports", "Sports")]
DEFAULT_DEPARTMENT_NAMES = {name for _, name in DEFAULT_DEPARTMENTS}


class SiteImage(Base):
    """Every non-product photo on the storefront (hero banners, editorial sections,
    category tiles, the Instagram/gallery grids) — purely visual/marketing, never
    tied to a specific product. `slot` identifies which named spot an image fills;
    see SITE_IMAGE_SLOTS. Admin-managed so none of this ever needs a code change."""
    __tablename__ = "site_images"

    id = Column(Integer, primary_key=True)
    slot = Column(String(50), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    heading = Column(String(200), default="")
    subheading = Column(String(300), default="")
    link_url = Column(String(300), default="")   # where it goes on click, e.g. men.html
    tag = Column(String(50), nullable=True)        # optional category tag — used by gallery_grid
    video_url = Column(String(500), nullable=True)  # optional companion video — plays when the photo is touched/clicked
    width = Column(Integer, nullable=True)        # intended display dimensions in px —
    height = Column(Integer, nullable=True)        # frontend uses these for aspect-ratio when set
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


SUBSCRIBER_CATEGORIES = ["men", "women", "other", "all"]


class Subscriber(Base):
    """Newsletter/offer subscribers captured from the homepage signup form.
    `category` is their stated interest (men/women/other/all) so admin can
    segment who gets which offer email."""
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(20), default="all")
    subscribed_at = Column(DateTime(timezone=True), server_default=func.now())


class Image(Base):
    """Every uploaded photo's actual bytes, stored in the database itself rather
    than as a loose file on disk. This is the single source of truth — wherever
    the database goes (backup, restore, a new server), the photos go with it,
    with nothing that can fall out of sync. Product photos, site photos, the
    payment QR code, and customer-uploaded payment proofs all use this."""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True)
    data = Column(LargeBinary, nullable=False)
    content_type = Column(String(100), default="image/jpeg")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Customer(Base):
    """Customer accounts — optional at checkout (guest checkout still works via
    Order having no customer_id), but enables order history, wishlist, and
    saved addresses when someone does create an account."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(80), default="")
    last_name = Column(String(80), default="")
    phone = Column(String(20), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    label = Column(String(40), default="Home")   # Home, Office, etc.
    full_name = Column(String(160), default="")
    phone = Column(String(20), default="")
    province = Column(String(50), default="")
    city = Column(String(80), default="")
    address = Column(String(300), default="")
    landmark = Column(String(200), default="")
    is_default = Column(Boolean, default=False)

    customer = relationship("Customer", back_populates="addresses")


class CustomerSession(Base):
    """Same httpOnly-cookie session pattern as AdminSession, for the customer
    account system (login, order history, wishlist)."""
    __tablename__ = "customer_sessions"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WishlistItem(Base):
    """Wishlist entries. Works for both signed-in customers (customer_id) and
    guests browsing anonymously (guest_token, a long-lived cookie) — mirroring
    how the cart already supports guest checkout without an account."""
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("customer_id", "guest_token", "product_id", name="uix_wishlist_item"),)

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    guest_token = Column(String(64), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")


COUPON_DISCOUNT_TYPES = ["percentage", "fixed"]


class Coupon(Base):
    """Admin-managed discount codes. category_slug/department scope the coupon
    to a subset of the catalog when set; blank means it applies storewide."""
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    discount_type = Column(String(20), nullable=False, default="percentage")   # percentage | fixed
    discount_value = Column(Integer, nullable=False)     # 10 = 10% if percentage, or NPR 10 if fixed
    min_order_value = Column(Integer, default=0)
    category_slug = Column(String(50), default="")        # restrict to men/women/unisex, blank = all
    department = Column(String(30), default="")           # restrict to a movement/style category, blank = all
    first_order_only = Column(Boolean, default=False)
    usage_limit = Column(Integer, nullable=True)           # total redemptions allowed, blank = unlimited
    times_used = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeliveryZone(Base):
    """Admin-managed delivery zones and their flat fees (Kathmandu, Pokhara,
    etc.) — replaces a single flat shipping fee with Nepal-realistic
    zone pricing."""
    __tablename__ = "delivery_zones"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    fee = Column(Integer, nullable=False, default=100)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

