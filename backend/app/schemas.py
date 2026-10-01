from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Products ----------

class ImageOut(BaseModel):
    id: int
    url: str
    sort_order: int
    color_name: str | None = None
    angle: str | None = None
    model_config = ConfigDict(from_attributes=True)


class SiteImageOut(BaseModel):
    id: int
    slot: str
    url: str
    heading: str
    subheading: str
    link_url: str
    tag: Optional[str] = None
    video_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sort_order: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class SiteImageUpdateIn(BaseModel):
    heading: Optional[str] = None
    subheading: Optional[str] = None
    link_url: Optional[str] = None
    tag: Optional[str] = None
    video_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ReviewOut(BaseModel):
    id: int
    product_id: int
    customer_name: str
    rating: int
    comment: str
    is_verified: bool  # True when order_id is set — computed, not stored directly
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, r):
        return cls(
            id=r.id, product_id=r.product_id, customer_name=r.customer_name,
            rating=r.rating, comment=r.comment, is_verified=r.order_id is not None,
            created_at=r.created_at,
        )


class ReviewIn(BaseModel):
    customer_name: str
    rating: int
    comment: str = ""
    order_number: str = ""   # optional — verifies purchase if it matches this product


class AdminReviewOut(ReviewOut):
    product_title: str = ""
    is_visible: bool = True


class ReturnRequestIn(BaseModel):
    reason: str
    email: str = ""
    phone: str = ""


class ReturnStatusIn(BaseModel):
    status: str
    admin_note: str = ""


class ReturnRequestOut(BaseModel):
    id: int
    order_id: int
    order_number: str = ""
    reason: str
    status: str
    admin_note: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ColorOut(BaseModel):
    id: int
    name: str
    hex_code: str
    model_config = ConfigDict(from_attributes=True)


class ColorIn(BaseModel):
    name: str
    hex_code: str = "#111111"


class VariantOut(BaseModel):
    id: int
    size: str
    color_name: str
    strap_material: str = ""
    sku: str = ""
    stock_qty: int
    image_url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class ProductCardOut(BaseModel):
    """Lightweight shape used in grid/listing views."""
    id: int
    slug: str
    title: str
    price: int
    compare_at_price: Optional[int] = None
    department: str = "Classic"
    subcategory: str
    category_slug: str
    is_new_arrival: bool
    is_best_seller: bool = False
    is_featured: bool = False
    is_limited_edition: bool = False
    display_rank: int = 0
    collection_tag: str
    brand_name: Optional[str] = None
    movement: str = ""
    case_material: str = ""
    dial_color: str = ""
    in_stock: bool = True
    available_sizes: list[str] = []
    available_straps: list[str] = []
    primary_image: Optional[str] = None
    secondary_image: Optional[str] = None
    video_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ProductDetailOut(BaseModel):
    id: int
    slug: str
    title: str
    price: int
    compare_at_price: Optional[int] = None
    description: str
    material: str
    department: str = "Classic"
    subcategory: str
    category_slug: str
    collection_tag: str
    is_new_arrival: bool
    is_best_seller: bool = False
    is_featured: bool = False
    is_limited_edition: bool = False
    display_rank: int = 0
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    model_name: str = ""
    reference_number: str = ""
    sku: str = ""
    movement: str = ""
    case_material: str = ""
    dial_color: str = ""
    strap_material: str = ""
    water_resistance: str = ""
    glass_type: str = ""
    warranty: str = ""
    condition: str = "new"
    has_certificate: bool = False
    video_url: Optional[str] = None
    images: list[ImageOut] = []
    colors: list[ColorOut] = []
    variants: list[VariantOut] = []
    avg_rating: Optional[float] = None
    review_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ProductIn(BaseModel):
    title: str
    category_slug: str          # gender: men | women | unisex
    department: str = "Classic"  # Automatic | Chronograph | Classic | Diver
    subcategory: str = ""
    price: int
    compare_at_price: Optional[int] = None
    description: str = ""
    material: str = ""
    collection_tag: str = ""
    is_new_arrival: bool = False
    is_best_seller: bool = False
    is_featured: bool = False
    is_limited_edition: bool = False
    display_rank: int = 0
    is_active: bool = True
    brand_id: Optional[int] = None
    model_name: str = ""
    reference_number: str = ""
    sku: str = ""
    movement: str = ""
    case_material: str = ""
    dial_color: str = ""
    strap_material: str = ""
    water_resistance: str = ""
    glass_type: str = ""
    warranty: str = ""
    condition: str = "new"
    has_certificate: bool = False
    video_url: Optional[str] = None
    colors: list[str] = []             # simple list of color names, hex optional via /colors endpoint
    sizes: list[str] = []              # sizes to create as zero-stock variants if not already present


class ProductUpdateIn(BaseModel):
    title: Optional[str] = None
    category_slug: Optional[str] = None
    department: Optional[str] = None
    subcategory: Optional[str] = None
    price: Optional[int] = None
    compare_at_price: Optional[int] = None
    description: Optional[str] = None
    material: Optional[str] = None
    collection_tag: Optional[str] = None
    is_new_arrival: Optional[bool] = None
    is_best_seller: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_limited_edition: Optional[bool] = None
    display_rank: Optional[int] = None
    is_active: Optional[bool] = None
    brand_id: Optional[int] = None
    model_name: Optional[str] = None
    reference_number: Optional[str] = None
    sku: Optional[str] = None
    movement: Optional[str] = None
    case_material: Optional[str] = None
    dial_color: Optional[str] = None
    strap_material: Optional[str] = None
    water_resistance: Optional[str] = None
    glass_type: Optional[str] = None
    warranty: Optional[str] = None
    condition: Optional[str] = None
    has_certificate: Optional[bool] = None
    video_url: Optional[str] = None


class VariantIn(BaseModel):
    size: str
    color_name: str = ""
    strap_material: str = ""
    sku: str = ""
    stock_qty: int = 0


class CategoryOut(BaseModel):
    slug: str
    name: str
    count: int = 0
    model_config = ConfigDict(from_attributes=True)


class CategoryIn(BaseModel):
    slug: str
    name: str


class DepartmentOut(BaseModel):
    slug: str
    name: str
    count: int = 0
    is_default: bool = False
    model_config = ConfigDict(from_attributes=True)


class DepartmentIn(BaseModel):
    slug: str
    name: str


# ---------- Cart ----------

class CartItemIn(BaseModel):
    product_id: int
    color: str = ""
    size: str = ""
    quantity: int = 1


class CartItemUpdateIn(BaseModel):
    quantity: Optional[int] = None
    size: Optional[str] = None


class CartItemOut(BaseModel):
    id: int
    product_id: int
    slug: str
    title: str
    color: str
    color_hex: Optional[str] = None
    size: str
    quantity: int
    unit_price: int
    line_total: int
    image: Optional[str] = None
    max_stock: Optional[int] = None


class CartOut(BaseModel):
    items: list[CartItemOut]
    subtotal: int
    shipping_fee: int
    total: int
    item_count: int


# ---------- Orders ----------

class OrderCreateIn(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    province: str
    city: str                    # District
    postal_code: str = ""
    payment_method: str          # "cod" | "mobile_banking"
    payment_reference: str = ""


class OrderItemOut(BaseModel):
    product_title: str
    color: str
    color_hex: Optional[str] = None
    size: str
    strap_material: str = ""
    sku: str = ""
    unit_price: int
    quantity: int
    line_total: int


class OrderOut(BaseModel):
    order_number: str
    status: str
    warranty_status: str = "active"
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    province: str
    city: str
    postal_code: str
    landmark: str = ""
    delivery_instructions: str = ""
    delivery_zone: str = ""
    coupon_code: Optional[str] = None
    discount_amount: int = 0
    payment_method: str
    subtotal: int
    shipping_fee: int
    total: int
    created_at: datetime
    items: list[OrderItemOut]
    email_sent: bool


class OrderAdminOut(OrderOut):
    id: int
    payment_reference: str
    payment_proof_path: str


class OrderStatusIn(BaseModel):
    status: str


class WarrantyStatusIn(BaseModel):
    warranty_status: str


# ---------- Admin auth ----------

class AdminLoginIn(BaseModel):
    username: str
    password: str


class AdminMeOut(BaseModel):
    username: str


# ---------- Settings ----------

class PublicSettingsOut(BaseModel):
    whatsapp_number: str
    merchant_name: str
    merchant_number: str
    qr_image_url: Optional[str] = None
    qr_images_by_method: dict = {}
    site_logo_url: Optional[str] = None
    brand_showcase_url: Optional[str] = None
    site_brand_name: str = "TIME-X"
    site_tagline: str = "Precision, crafted. Timeless. Premium watches from Kathmandu."
    cod_enabled: bool
    mobile_banking_enabled: bool
    contact_phone: str = ""
    instagram_url: str = ""
    tiktok_url: str = ""
    free_delivery_enabled: bool = False
    free_delivery_threshold: int = 0


class SettingsUpdateIn(BaseModel):
    whatsapp_number: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_number: Optional[str] = None
    cod_enabled: Optional[bool] = None
    mobile_banking_enabled: Optional[bool] = None
    contact_phone: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    site_brand_name: Optional[str] = None
    site_tagline: Optional[str] = None
    free_delivery_enabled: Optional[bool] = None
    free_delivery_threshold: Optional[int] = None


# ---------- Ledger (income/expenses) ----------

class ExpenseIn(BaseModel):
    category: str
    amount: int
    note: str = ""
    expense_date: date
    is_recurring: bool = False


class ExpenseUpdateIn(BaseModel):
    category: Optional[str] = None
    amount: Optional[int] = None
    note: Optional[str] = None
    expense_date: Optional[date] = None
    is_recurring: Optional[bool] = None


class ExpenseOut(BaseModel):
    id: int
    category: str
    amount: int
    note: str
    expense_date: date
    is_recurring: bool
    model_config = ConfigDict(from_attributes=True)


class LedgerSummaryOut(BaseModel):
    start_date: date
    end_date: date
    income_total: int
    order_count: int
    expense_total: int
    net: int
    expense_by_category: dict[str, int]


class SubscriberIn(BaseModel):
    email: str
    category: str = "all"


class SubscriberOut(BaseModel):
    id: int
    email: str
    category: str
    subscribed_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SendOfferIn(BaseModel):
    subscriber_ids: list[int]
    message: str
    subject: str = "A message from TIME-X"


# ---------- Brands ----------

class BrandOut(BaseModel):
    id: int
    slug: str
    name: str
    logo_url: Optional[str] = None
    count: int = 0
    model_config = ConfigDict(from_attributes=True)


class BrandIn(BaseModel):
    slug: str
    name: str


# ---------- Delivery Zones ----------

class DeliveryZoneOut(BaseModel):
    id: int
    name: str
    fee: int
    sort_order: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class DeliveryZoneIn(BaseModel):
    name: str
    fee: int


class DeliveryZoneUpdateIn(BaseModel):
    name: Optional[str] = None
    fee: Optional[int] = None
    is_active: Optional[bool] = None


# ---------- Coupons ----------

class CouponOut(BaseModel):
    id: int
    code: str
    discount_type: str
    discount_value: int
    min_order_value: int
    category_slug: str
    department: str
    first_order_only: bool
    usage_limit: Optional[int] = None
    times_used: int
    expires_at: Optional[datetime] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class CouponIn(BaseModel):
    code: str
    discount_type: str = "percentage"
    discount_value: int
    min_order_value: int = 0
    category_slug: str = ""
    department: str = ""
    first_order_only: bool = False
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None


class CouponUpdateIn(BaseModel):
    discount_value: Optional[int] = None
    min_order_value: Optional[int] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponApplyIn(BaseModel):
    code: str
    subtotal: int
    email: Optional[str] = None


class CouponApplyOut(BaseModel):
    valid: bool
    discount_amount: int = 0
    message: str = ""


# ---------- Customer accounts ----------

class CustomerRegisterIn(BaseModel):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    phone: str = ""


class CustomerLoginIn(BaseModel):
    email: str
    password: str


class CustomerOut(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CustomerAddressIn(BaseModel):
    label: str = "Home"
    full_name: str
    phone: str
    province: str
    city: str
    address: str
    landmark: str = ""
    is_default: bool = False


class CustomerAddressOut(BaseModel):
    id: int
    label: str
    full_name: str
    phone: str
    province: str
    city: str
    address: str
    landmark: str
    is_default: bool
    model_config = ConfigDict(from_attributes=True)


# ---------- Wishlist ----------

class WishlistItemOut(BaseModel):
    id: int
    product_id: int
    slug: str
    title: str
    price: int
    compare_at_price: Optional[int] = None
    image: Optional[str] = None
    in_stock: bool = True
    added_at: datetime


class StockAdjustIn(BaseModel):
    new_stock_qty: int
    reason: str = "manual_adjustment"   # manual_adjustment | damaged | restock
    note: str = ""

