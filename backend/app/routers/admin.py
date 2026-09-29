import os
import re
import uuid
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from .. import models, schemas, config, auth
from ..database import get_db
from ..settings_utils import get_setting, set_setting
from ..image_utils import save_image_to_db, delete_image_by_url
from ..email_utils import send_simple_email, render_return_email_html, render_offer_email_html
from .orders import restore_stock_for_order, take_stock_for_order

router = APIRouter(prefix="/api/admin", tags=["admin"])


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "product"


def unique_slug(db: Session, title: str, existing_id: int | None = None) -> str:
    base = slugify(title)
    slug = base
    n = 2
    while True:
        q = db.query(models.Product).filter(models.Product.slug == slug)
        if existing_id:
            q = q.filter(models.Product.id != existing_id)
        if not q.first():
            return slug
        slug = f"{base}-{n}"
        n += 1


# ---------------------------------------------------------------- auth ----

@router.post("/login")
def login(payload: schemas.AdminLoginIn, response: Response, db: Session = Depends(get_db)):
    admin = db.query(models.AdminUser).filter(models.AdminUser.username == payload.username).first()
    if not admin or not auth.verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = auth.create_session(db, admin.id)
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME, value=token,
        httponly=True, samesite="lax", secure=config.COOKIE_SECURE, domain=config.COOKIE_DOMAIN, path="/", max_age=60 * 60 * 24 * config.SESSION_TTL_DAYS,
    )
    return {"ok": True, "username": admin.username}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if token:
        auth.destroy_session(db, token)
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/", domain=config.COOKIE_DOMAIN)
    return {"ok": True}


@router.get("/me", response_model=schemas.AdminMeOut)
def me(admin: models.AdminUser = Depends(auth.get_current_admin)):
    return schemas.AdminMeOut(username=admin.username)


# --------------------------------------------------------------- products --

@router.get("/products")
def list_all_products(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    products = (
        db.query(models.Product)
        .options(joinedload(models.Product.images), joinedload(models.Product.variants),
                  joinedload(models.Product.colors), joinedload(models.Product.category))
        .order_by(models.Product.created_at.desc())
        .all()
    )
    out = []
    for p in products:
        out.append({
            "id": p.id, "slug": p.slug, "title": p.title, "price": p.price, "compare_at_price": p.compare_at_price,
            "category_slug": p.category.slug, "department": p.department or "Clothing", "subcategory": p.subcategory,
            "collection_tag": p.collection_tag, "is_new_arrival": p.is_new_arrival,
            "is_active": p.is_active, "image": p.images[0].url if p.images else None,
            "total_stock": sum(v.stock_qty for v in p.variants),
            "variant_count": len(p.variants),
            "variants": [
                {"id": v.id, "size": v.size, "color_name": v.color_name, "strap_material": v.strap_material,
                 "sku": v.sku, "stock_qty": v.stock_qty}
                for v in p.variants
            ],
        })
    return out


@router.post("/products", response_model=schemas.ProductDetailOut)
def create_product(payload: schemas.ProductIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    category = db.query(models.Category).filter(models.Category.slug == payload.category_slug).first()
    if not category:
        raise HTTPException(status_code=400, detail=f"Unknown category '{payload.category_slug}'")

    product = models.Product(
        slug=unique_slug(db, payload.title), title=payload.title, category_id=category.id,
        department=payload.department, subcategory=payload.subcategory,
        price=payload.price, compare_at_price=payload.compare_at_price, description=payload.description,
        material=payload.material, collection_tag=payload.collection_tag,
        is_new_arrival=payload.is_new_arrival, is_best_seller=payload.is_best_seller,
        is_featured=payload.is_featured, is_limited_edition=payload.is_limited_edition,
        is_active=payload.is_active,
        brand_id=payload.brand_id, model_name=payload.model_name or payload.title,
        reference_number=payload.reference_number, sku=payload.sku,
        movement=payload.movement, case_material=payload.case_material, dial_color=payload.dial_color,
        strap_material=payload.strap_material, water_resistance=payload.water_resistance,
        glass_type=payload.glass_type, warranty=payload.warranty, condition=payload.condition,
        has_certificate=payload.has_certificate, video_url=payload.video_url,
    )
    db.add(product)
    db.flush()

    for color_name in payload.colors:
        db.add(models.ProductColor(product_id=product.id, name=color_name))
    for size in payload.sizes:
        db.add(models.ProductVariant(product_id=product.id, size=size, color_name="", stock_qty=0))

    db.commit()
    db.refresh(product)
    return _product_detail(product)


def _product_detail(p: models.Product) -> schemas.ProductDetailOut:
    return schemas.ProductDetailOut(
        id=p.id, slug=p.slug, title=p.title, price=p.price, compare_at_price=p.compare_at_price,
        description=p.description or "", material=p.material or "",
        department=p.department or "Classic", subcategory=p.subcategory or "", category_slug=p.category.slug,
        collection_tag=p.collection_tag or "", is_new_arrival=p.is_new_arrival,
        is_best_seller=p.is_best_seller, is_featured=p.is_featured, is_limited_edition=p.is_limited_edition,
        brand_id=p.brand_id, brand_name=p.brand.name if p.brand else None,
        model_name=p.model_name or "", reference_number=p.reference_number or "", sku=p.sku or "",
        movement=p.movement or "", case_material=p.case_material or "", dial_color=p.dial_color or "",
        strap_material=p.strap_material or "", water_resistance=p.water_resistance or "",
        glass_type=p.glass_type or "", warranty=p.warranty or "", condition=p.condition or "new",
        has_certificate=p.has_certificate, video_url=p.video_url,
        images=[schemas.ImageOut.model_validate(i) for i in sorted(p.images, key=lambda i: i.sort_order)],
        colors=[schemas.ColorOut.model_validate(c) for c in p.colors],
        variants=[schemas.VariantOut.model_validate(v) for v in p.variants],
    )


def _get_product_or_404(db: Session, product_id: int) -> models.Product:
    p = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p


@router.get("/products/{product_id}", response_model=schemas.ProductDetailOut)
def get_admin_product(product_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    return _product_detail(_get_product_or_404(db, product_id))


@router.put("/products/{product_id}", response_model=schemas.ProductDetailOut)
def update_product(product_id: int, payload: schemas.ProductUpdateIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    data = payload.model_dump(exclude_unset=True)

    if "category_slug" in data:
        category = db.query(models.Category).filter(models.Category.slug == data.pop("category_slug")).first()
        if not category:
            raise HTTPException(status_code=400, detail="Unknown category")
        product.category_id = category.id
    if "title" in data and data["title"] and data["title"] != product.title:
        product.title = data.pop("title")
        product.slug = unique_slug(db, product.title, existing_id=product.id)
    for field, value in data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _product_detail(product)


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    for img in product.images:
        delete_image_by_url(db, img.url)
    db.delete(product)
    db.commit()
    return {"ok": True}


@router.post("/products/{product_id}/images", response_model=schemas.ProductDetailOut)
async def upload_product_image(product_id: int, file: UploadFile = File(...), color_name: str = Form(""), db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    color_name = color_name.strip()
    if color_name and not any(c.name == color_name for c in product.colors):
        raise HTTPException(status_code=400, detail=f"'{color_name}' isn't one of this product's colors yet — add it as a color first.")
    content = await file.read()
    url = save_image_to_db(db, content, file.content_type)

    next_order = max([i.sort_order for i in product.images], default=-1) + 1
    db.add(models.ProductImage(
        product_id=product.id, url=url, sort_order=next_order,
        color_name=color_name or None,
    ))
    db.commit()
    db.refresh(product)
    return _product_detail(product)


@router.delete("/products/{product_id}/images/{image_id}", response_model=schemas.ProductDetailOut)
def delete_product_image(product_id: int, image_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    img = db.query(models.ProductImage).filter(
        models.ProductImage.id == image_id, models.ProductImage.product_id == product_id
    ).first()
    if img:
        delete_image_by_url(db, img.url)
        db.delete(img)
        db.commit()
        db.refresh(product)
    return _product_detail(product)


@router.post("/products/{product_id}/video", response_model=schemas.ProductDetailOut)
async def upload_product_video(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    """Uploads a short companion video for this product — plays when the
    customer touches/hovers the primary photo on the product page."""
    product = _get_product_or_404(db, product_id)
    delete_image_by_url(db, product.video_url)

    content = await file.read()
    url = save_image_to_db(db, content, file.content_type)
    product.video_url = url
    db.commit()
    db.refresh(product)
    return _product_detail(product)


@router.delete("/products/{product_id}/video", response_model=schemas.ProductDetailOut)
def delete_product_video(product_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    if product.video_url:
        delete_image_by_url(db, product.video_url)
        product.video_url = None
        db.commit()
        db.refresh(product)
    return _product_detail(product)


@router.post("/products/{product_id}/colors", response_model=schemas.ProductDetailOut)
def add_product_color(product_id: int, payload: schemas.ColorIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Color name is required")
    existing = db.query(models.ProductColor).filter(
        models.ProductColor.product_id == product_id, models.ProductColor.name == name
    ).first()
    if existing:
        existing.hex_code = payload.hex_code
    else:
        db.add(models.ProductColor(product_id=product_id, name=name, hex_code=payload.hex_code))
    db.commit()
    db.refresh(product)
    return _product_detail(product)


@router.delete("/products/{product_id}/colors/{color_id}", response_model=schemas.ProductDetailOut)
def delete_product_color(product_id: int, color_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    color = db.query(models.ProductColor).filter(
        models.ProductColor.id == color_id, models.ProductColor.product_id == product_id
    ).first()
    if color:
        # Also drop any variants tied to this color name so stock/checkout never
        # references a color that no longer has a visible swatch.
        db.query(models.ProductVariant).filter(
            models.ProductVariant.product_id == product_id, models.ProductVariant.color_name == color.name
        ).delete()
        db.delete(color)
        db.commit()
        db.refresh(product)
    return _product_detail(product)


@router.post("/products/{product_id}/variants", response_model=schemas.ProductDetailOut)
def upsert_variant(product_id: int, payload: schemas.VariantIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    existing = db.query(models.ProductVariant).filter(
        models.ProductVariant.product_id == product_id,
        models.ProductVariant.size == payload.size,
        models.ProductVariant.color_name == payload.color_name,
        models.ProductVariant.strap_material == payload.strap_material,
    ).first()
    if existing:
        existing.stock_qty = payload.stock_qty
        if payload.sku:
            existing.sku = payload.sku
    else:
        db.add(models.ProductVariant(
            product_id=product_id, size=payload.size,
            color_name=payload.color_name, strap_material=payload.strap_material,
            sku=payload.sku, stock_qty=payload.stock_qty,
        ))
    db.commit()
    db.refresh(product)
    return _product_detail(product)


@router.patch("/variants/{variant_id}/stock")
def adjust_variant_stock(variant_id: int, payload: schemas.StockAdjustIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    if payload.new_stock_qty < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")
    change = payload.new_stock_qty - variant.stock_qty
    variant.stock_qty = payload.new_stock_qty
    if change != 0:
        db.add(models.StockHistoryEntry(variant_id=variant_id, change=change, reason=payload.reason, note=payload.note))
    db.commit()
    return {"ok": True, "variant_id": variant_id, "new_stock_qty": variant.stock_qty}


@router.get("/variants/{variant_id}/stock-history")
def get_stock_history(variant_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    entries = (
        db.query(models.StockHistoryEntry)
        .filter(models.StockHistoryEntry.variant_id == variant_id)
        .order_by(models.StockHistoryEntry.created_at.desc())
        .limit(50)
        .all()
    )
    return [{"change": e.change, "reason": e.reason, "note": e.note, "created_at": e.created_at} for e in entries]


@router.delete("/products/{product_id}/variants/{variant_id}", response_model=schemas.ProductDetailOut)
def delete_variant(product_id: int, variant_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    product = _get_product_or_404(db, product_id)
    v = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id, models.ProductVariant.product_id == product_id
    ).first()
    if v:
        db.delete(v)
        db.commit()
        db.refresh(product)
    return _product_detail(product)


# --------------------------------------------------------------- customers --

@router.get("/customers")
def list_customers(
    product_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
    db: Session = Depends(get_db),
    admin: models.AdminUser = Depends(auth.get_current_admin),
):
    """Every registered customer with their purchase summary, filterable by
    a product they've bought, an order date range, and their total spend.
    Guest checkouts (orders with no customer_id) aren't included here since
    there's no account to attach them to."""
    customers = db.query(models.Customer).order_by(models.Customer.created_at.desc()).all()

    results = []
    for c in customers:
        orders_q = db.query(models.Order).filter(models.Order.customer_id == c.id)
        if date_from:
            orders_q = orders_q.filter(func.date(models.Order.created_at) >= date_from)
        if date_to:
            orders_q = orders_q.filter(func.date(models.Order.created_at) <= date_to)
        if product_id:
            orders_q = orders_q.join(models.OrderItem).filter(models.OrderItem.product_id == product_id)
        orders = orders_q.options(joinedload(models.Order.items)).all()

        total_spent = sum(o.total for o in orders)
        if min_amount is not None and total_spent < min_amount:
            continue
        if max_amount is not None and total_spent > max_amount:
            continue
        # With any filter active, only show customers who actually have a matching order.
        if (product_id or date_from or date_to) and not orders:
            continue

        products_bought = sorted({item.product_title for o in orders for item in o.items})
        own_name = f"{c.first_name} {c.last_name}".strip()
        if not own_name and orders:
            latest_order = max(orders, key=lambda o: o.created_at)
            own_name = f"{latest_order.first_name} {latest_order.last_name}".strip()

        results.append({
            "id": c.id, "name": own_name or c.email, "email": c.email,
            "phone": c.phone, "joined": c.created_at.isoformat(),
            "order_count": len(orders), "total_spent": total_spent,
            "last_order_date": max((o.created_at for o in orders), default=None),
            "products_bought": products_bought,
        })
        if results[-1]["last_order_date"] is not None:
            results[-1]["last_order_date"] = results[-1]["last_order_date"].isoformat()

    return results


# ----------------------------------------------------------------- orders --

@router.get("/orders")
def list_orders(status: str | None = None, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    q = db.query(models.Order).options(joinedload(models.Order.items)).order_by(models.Order.created_at.desc())
    if status:
        q = q.filter(models.Order.status == status)
    orders = q.all()
    return [
        {
            "id": o.id, "order_number": o.order_number, "status": o.status,
            "warranty_status": o.warranty_status or "active",
            "customer": f"{o.first_name} {o.last_name}", "email": o.email, "phone": o.phone,
            "payment_method": o.payment_method, "total": o.total,
            "item_count": sum(i.quantity for i in o.items),
            "created_at": o.created_at.isoformat(),
        }
        for o in orders
    ]


@router.get("/orders/{order_id}")
def get_admin_order(order_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    o = db.query(models.Order).options(joinedload(models.Order.items)).filter(models.Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": o.id, "order_number": o.order_number, "status": o.status,
        "warranty_status": o.warranty_status or "active",
        "first_name": o.first_name, "last_name": o.last_name, "email": o.email, "phone": o.phone,
        "address": o.address, "province": o.province, "city": o.city, "postal_code": o.postal_code,
        "payment_method": o.payment_method, "payment_reference": o.payment_reference,
        "payment_proof_path": o.payment_proof_path,
        "subtotal": o.subtotal, "shipping_fee": o.shipping_fee, "total": o.total,
        "email_sent": o.email_sent, "created_at": o.created_at.isoformat(),
        "items": [
            {"product_title": i.product_title, "color": i.color, "color_hex": i.color_hex, "size": i.size,
             "unit_price": i.unit_price, "quantity": i.quantity, "line_total": i.unit_price * i.quantity}
            for i in o.items
        ],
    }


VALID_STATUSES = set(models.ORDER_STATUSES)


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, payload: schemas.OrderStatusIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {sorted(VALID_STATUSES)}")
    o = db.query(models.Order).options(joinedload(models.Order.items)).filter(models.Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    was_cancelled = o.status == "cancelled"
    now_cancelled = payload.status == "cancelled"
    if now_cancelled and not was_cancelled:
        restore_stock_for_order(db, o)
    elif was_cancelled and not now_cancelled:
        take_stock_for_order(db, o)

    o.status = payload.status
    db.commit()
    return {"ok": True, "status": o.status}


VALID_WARRANTY_STATUSES = {"active", "claimed", "void", "expired"}


@router.patch("/orders/{order_id}/warranty-status")
def update_warranty_status(order_id: int, payload: schemas.WarrantyStatusIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    if payload.warranty_status not in VALID_WARRANTY_STATUSES:
        raise HTTPException(status_code=400, detail=f"warranty_status must be one of {sorted(VALID_WARRANTY_STATUSES)}")
    o = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.warranty_status = payload.warranty_status
    db.commit()
    return {"ok": True, "warranty_status": o.warranty_status}


# --------------------------------------------------------------- settings --

@router.get("/settings")
def get_admin_settings(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    return {
        "whatsapp_number": get_setting(db, "whatsapp_number", config.WHATSAPP_DEFAULT),
        "merchant_name": get_setting(db, "merchant_name", "TIME-X"),
        "merchant_number": get_setting(db, "merchant_number", ""),
        "qr_image_url": get_setting(db, "qr_image_path", "") or None,
        "qr_images_by_method": {
            method: get_setting(db, f"qr_image_path_{method}", "") or get_setting(db, "qr_image_path", "") or None
            for method in ("esewa", "khalti", "fonepay", "connectips", "bank_transfer")
        },
        "site_logo_url": get_setting(db, "site_logo_path", "") or None,
        "brand_showcase_url": get_setting(db, "brand_showcase_path", "") or None,
        "site_brand_name": get_setting(db, "site_brand_name", "TIME-X"),
        "site_tagline": get_setting(db, "site_tagline", "Precision, crafted. Timeless. Premium watches from Kathmandu."),
        "cod_enabled": get_setting(db, "cod_enabled", "true") == "true",
        "mobile_banking_enabled": get_setting(db, "mobile_banking_enabled", "true") == "true",
        "contact_phone": get_setting(db, "contact_phone", config.WHATSAPP_DEFAULT),
        "instagram_url": get_setting(db, "instagram_url", ""),
        "tiktok_url": get_setting(db, "tiktok_url", ""),
        "free_delivery_enabled": get_setting(db, "free_delivery_enabled", "false") == "true",
        "free_delivery_threshold": int(get_setting(db, "free_delivery_threshold", "5000")),
    }


@router.put("/settings")
def update_admin_settings(payload: schemas.SettingsUpdateIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        set_setting(db, key, "true" if value is True else "false" if value is False else str(value))
    db.commit()
    return get_admin_settings(db=db, admin=admin)


QR_PAYMENT_METHODS = {"esewa", "khalti", "fonepay", "connectips", "bank_transfer"}


@router.post("/settings/qr")
async def upload_qr(method: str = Form(""), file: UploadFile = File(...), db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    """Uploads a QR code. If `method` is one of the known payment methods, it's
    saved as that method's own QR (settings key qr_image_path_<method>) so each
    payment option can show its correct code at checkout. With no method given,
    falls back to the original shared QR (qr_image_path) for backward
    compatibility with sites that haven't set per-method QRs yet."""
    if method and method not in QR_PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail=f"method must be one of {sorted(QR_PAYMENT_METHODS)} or left blank")

    setting_key = f"qr_image_path_{method}" if method else "qr_image_path"
    old_url = get_setting(db, setting_key, "")
    delete_image_by_url(db, old_url)

    content = await file.read()
    url = save_image_to_db(db, content, file.content_type)
    set_setting(db, setting_key, url)
    db.commit()
    return {"qr_image_url": url, "method": method or None}


@router.post("/settings/logo")
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    old_url = get_setting(db, "site_logo_path", "")
    delete_image_by_url(db, old_url)

    content = await file.read()
    url = save_image_to_db(db, content, file.content_type)
    set_setting(db, "site_logo_path", url)
    db.commit()
    return {"site_logo_url": url}


# ----------------------------------------------------------- ledger (income/expenses) --

EXPENSE_CATEGORIES = ["Rent", "Wages", "Inventory", "Packaging & Shipping", "Marketing", "Utilities", "Other"]


def _validate_category(category: str) -> None:
    if category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Category must be one of {EXPENSE_CATEGORIES}")


@router.get("/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(
    start_date: date | None = None, end_date: date | None = None,
    db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin),
):
    q = db.query(models.Expense).order_by(models.Expense.expense_date.desc(), models.Expense.id.desc())
    if start_date:
        q = q.filter(models.Expense.expense_date >= start_date)
    if end_date:
        q = q.filter(models.Expense.expense_date <= end_date)
    return [schemas.ExpenseOut.model_validate(e) for e in q.all()]


@router.post("/expenses", response_model=schemas.ExpenseOut)
def create_expense(payload: schemas.ExpenseIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    _validate_category(payload.category)
    expense = models.Expense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return schemas.ExpenseOut.model_validate(expense)


@router.put("/expenses/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(expense_id: int, payload: schemas.ExpenseUpdateIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    data = payload.model_dump(exclude_unset=True)
    if "category" in data:
        _validate_category(data["category"])
    for field, value in data.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return schemas.ExpenseOut.model_validate(expense)


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()
    return {"ok": True}


@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    from datetime import datetime, timedelta, timezone
    import collections

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    non_cancelled = models.Order.status.notin_(["cancelled", "failed"])

    todays_orders = db.query(models.Order).filter(models.Order.created_at >= today_start, non_cancelled).all()
    today_sales = sum(o.total for o in todays_orders)

    total_orders = db.query(models.Order).filter(non_cancelled).count()
    total_products = db.query(models.Product).filter(models.Product.is_active == True).count()  # noqa: E712
    total_customers = db.query(models.Customer).count()

    low_stock_count = (
        db.query(models.ProductVariant)
        .filter(models.ProductVariant.stock_qty > 0, models.ProductVariant.stock_qty <= 5)
        .count()
    )
    out_of_stock_count = db.query(models.ProductVariant).filter(models.ProductVariant.stock_qty == 0).count()

    # Best-selling — aggregate quantity sold per product across non-cancelled orders.
    sold_counter = collections.Counter()
    items = (
        db.query(models.OrderItem)
        .join(models.Order)
        .filter(non_cancelled)
        .all()
    )
    for item in items:
        sold_counter[item.product_title] += item.quantity
    best_sellers = [{"title": title, "quantity_sold": qty} for title, qty in sold_counter.most_common(5)]

    # Payment method breakdown.
    payment_counter = collections.Counter()
    all_orders = db.query(models.Order).filter(non_cancelled).all()
    for o in all_orders:
        payment_counter[o.payment_method] += 1
    payment_breakdown = [{"method": m, "count": c} for m, c in payment_counter.most_common()]

    # Sales by day, last 14 days.
    fourteen_days_ago = today_start - timedelta(days=13)
    recent_orders = db.query(models.Order).filter(models.Order.created_at >= fourteen_days_ago, non_cancelled).all()
    daily_totals = collections.defaultdict(int)
    for o in recent_orders:
        day_key = o.created_at.strftime("%Y-%m-%d")
        daily_totals[day_key] += o.total
    sales_by_day = [
        {"date": (fourteen_days_ago + timedelta(days=i)).strftime("%Y-%m-%d"),
         "total": daily_totals.get((fourteen_days_ago + timedelta(days=i)).strftime("%Y-%m-%d"), 0)}
        for i in range(14)
    ]

    return {
        "today_sales": today_sales, "today_order_count": len(todays_orders),
        "total_orders": total_orders, "total_products": total_products,
        "total_customers": total_customers,
        "low_stock_count": low_stock_count, "out_of_stock_count": out_of_stock_count,
        "best_sellers": best_sellers, "payment_breakdown": payment_breakdown,
        "sales_by_day": sales_by_day,
    }


@router.get("/ledger/summary", response_model=schemas.LedgerSummaryOut)
def ledger_summary(
    start_date: date, end_date: date,
    db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin),
):
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must not be before start_date")

    range_start = datetime.combine(start_date, time.min)
    range_end = datetime.combine(end_date, time.max)

    orders = db.query(models.Order).filter(
        models.Order.status != "cancelled",
        models.Order.created_at >= range_start,
        models.Order.created_at <= range_end,
    ).all()
    income_total = sum(o.total for o in orders)

    expenses = db.query(models.Expense).filter(
        models.Expense.expense_date >= start_date, models.Expense.expense_date <= end_date,
    ).all()
    expense_total = sum(e.amount for e in expenses)
    by_category: dict[str, int] = {}
    for e in expenses:
        by_category[e.category] = by_category.get(e.category, 0) + e.amount

    return schemas.LedgerSummaryOut(
        start_date=start_date, end_date=end_date,
        income_total=income_total, order_count=len(orders),
        expense_total=expense_total, net=income_total - expense_total,
        expense_by_category=by_category,
    )


# ----------------------------------------------------------- site images (every non-product photo) --

@router.get("/site-images/slots")
def list_site_image_slots(admin: models.AdminUser = Depends(auth.get_current_admin)):
    return [
        {"slot": slot, "label": label, "mode": mode, "page": page, "is_video": slot in models.VIDEO_SLOTS}
        for slot, (label, mode, page) in models.SITE_IMAGE_SLOTS.items()
    ]


@router.get("/site-images", response_model=list[schemas.SiteImageOut])
def list_site_images(slot: str | None = None, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    q = db.query(models.SiteImage)
    if slot:
        q = q.filter(models.SiteImage.slot == slot)
    return q.order_by(models.SiteImage.slot, models.SiteImage.sort_order).all()


@router.post("/site-images", response_model=schemas.SiteImageOut)
async def upload_site_image(
    slot: str = Form(...),
    file: UploadFile = File(...),
    heading: str = Form(""),
    subheading: str = Form(""),
    link_url: str = Form(""),
    tag: str | None = Form(None),
    width: int | None = Form(None),
    height: int | None = Form(None),
    db: Session = Depends(get_db),
    admin: models.AdminUser = Depends(auth.get_current_admin),
):
    if slot not in models.SITE_IMAGE_SLOTS:
        raise HTTPException(status_code=400, detail=f"Unknown slot '{slot}'")
    label, mode, page = models.SITE_IMAGE_SLOTS[slot]

    if slot == "gallery_grid":
        if not tag or tag not in models.GALLERY_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Choose a category for this photo: one of {list(models.GALLERY_CATEGORIES.keys())}")
    else:
        tag = None  # tag is only meaningful for gallery_grid — ignore it elsewhere

    content = await file.read()

    # If the admin didn't type dimensions, read the real ones from the file itself —
    # asked for, not required, and never wrong since it comes from the actual upload.
    # Video slots skip this entirely — PIL can't open a video file, and dimensions
    # aren't meaningful for a background video anyway.
    if slot in models.VIDEO_SLOTS:
        width, height = None, None
    elif width is None or height is None:
        try:
            import io
            from PIL import Image as PILImage
            with PILImage.open(io.BytesIO(content)) as img:
                width, height = img.size
        except Exception:
            width, height = None, None

    url = save_image_to_db(db, content, file.content_type)

    # Single-image slots (a page's one hero banner, one tile) replace whatever was
    # active before, rather than accumulating orphaned old versions.
    if mode == "single":
        old = db.query(models.SiteImage).filter(models.SiteImage.slot == slot, models.SiteImage.is_active == True).all()  # noqa: E712
        for old_image in old:
            delete_image_by_url(db, old_image.url)
        db.query(models.SiteImage).filter(models.SiteImage.slot == slot).update({"is_active": False})

    next_order = db.query(models.SiteImage).filter(models.SiteImage.slot == slot).count()
    image = models.SiteImage(
        slot=slot, url=url, heading=heading.strip(), subheading=subheading.strip(),
        link_url=link_url.strip(), tag=tag, width=width, height=height, sort_order=next_order, is_active=True,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.patch("/site-images/{image_id}", response_model=schemas.SiteImageOut)
def update_site_image(image_id: int, payload: schemas.SiteImageUpdateIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    image = db.query(models.SiteImage).filter(models.SiteImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Site image not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(image, field, value)
    db.commit()
    db.refresh(image)
    return image


@router.delete("/site-images/{image_id}")
def delete_site_image(image_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    image = db.query(models.SiteImage).filter(models.SiteImage.id == image_id).first()
    if image:
        delete_image_by_url(db, image.url)
        db.delete(image)
        db.commit()
    return {"ok": True}


# ----------------------------------------------------------- reviews (moderation) --

@router.get("/reviews", response_model=list[schemas.AdminReviewOut])
def list_all_reviews(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    reviews = (
        db.query(models.Review)
        .options(joinedload(models.Review.product))
        .order_by(models.Review.created_at.desc())
        .all()
    )
    out = []
    for r in reviews:
        base = schemas.ReviewOut.from_model(r)
        out.append(schemas.AdminReviewOut(
            **base.model_dump(), product_title=r.product.title if r.product else "(deleted product)",
            is_visible=r.is_visible,
        ))
    return out


@router.patch("/reviews/{review_id}", response_model=schemas.AdminReviewOut)
def set_review_visibility(review_id: int, is_visible: bool, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    review = db.query(models.Review).options(joinedload(models.Review.product)).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.is_visible = is_visible
    db.commit()
    db.refresh(review)
    base = schemas.ReviewOut.from_model(review)
    return schemas.AdminReviewOut(**base.model_dump(), product_title=review.product.title if review.product else "(deleted product)", is_visible=review.is_visible)


@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if review:
        db.delete(review)
        db.commit()
    return {"ok": True}


# ----------------------------------------------------------- returns --

@router.get("/returns", response_model=list[schemas.ReturnRequestOut])
def list_all_returns(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    returns = (
        db.query(models.ReturnRequest)
        .options(joinedload(models.ReturnRequest.order))
        .order_by(models.ReturnRequest.created_at.desc())
        .all()
    )
    return [
        schemas.ReturnRequestOut(
            id=r.id, order_id=r.order_id, order_number=r.order.order_number if r.order else "",
            reason=r.reason, status=r.status, admin_note=r.admin_note,
            created_at=r.created_at, updated_at=r.updated_at,
        ) for r in returns
    ]


@router.patch("/returns/{return_id}", response_model=schemas.ReturnRequestOut)
def update_return_status(return_id: int, payload: schemas.ReturnStatusIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    ret = db.query(models.ReturnRequest).options(joinedload(models.ReturnRequest.order)).filter(models.ReturnRequest.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    if payload.status not in models.RETURN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {models.RETURN_STATUSES}")

    ret.status = payload.status
    if payload.admin_note:
        ret.admin_note = payload.admin_note.strip()
    db.commit()
    db.refresh(ret)

    if ret.order:
        send_simple_email(
            ret.order.email, f"Return Update — Order #{ret.order.order_number}",
            render_return_email_html(ret.order, ret),
        )

    return schemas.ReturnRequestOut(
        id=ret.id, order_id=ret.order_id, order_number=ret.order.order_number if ret.order else "",
        reason=ret.reason, status=ret.status, admin_note=ret.admin_note,
        created_at=ret.created_at, updated_at=ret.updated_at,
    )


# ----------------------------------------------------------- categories (gender/audience) --

@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories_admin(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    cats = db.query(models.Category).all()
    return [
        schemas.CategoryOut(slug=c.slug, name=c.name, count=len(c.products))
        for c in cats
    ]


@router.post("/categories", response_model=schemas.CategoryOut)
def create_category(payload: schemas.CategoryIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    slug = payload.slug.strip().lower().replace(" ", "-")
    name = payload.name.strip()
    if not slug or not name:
        raise HTTPException(status_code=400, detail="Both a slug and a display name are required")
    if db.query(models.Category).filter(models.Category.slug == slug).first():
        raise HTTPException(status_code=400, detail=f"A category with slug '{slug}' already exists")
    cat = models.Category(slug=slug, name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return schemas.CategoryOut(slug=cat.slug, name=cat.name, count=0)


@router.delete("/categories/{slug}")
def delete_category(slug: str, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    cat = db.query(models.Category).filter(models.Category.slug == slug).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.products:
        raise HTTPException(status_code=400, detail=f"Can't delete '{cat.name}' — {len(cat.products)} product(s) still use it. Move or delete those first.")
    db.delete(cat)
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------- departments (product category) --

@router.get("/departments", response_model=list[schemas.DepartmentOut])
def list_departments_admin(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    depts = db.query(models.Department).all()
    return [
        schemas.DepartmentOut(
            slug=d.slug, name=d.name,
            count=db.query(models.Product).filter(models.Product.department == d.name).count(),
            is_default=d.name in models.DEFAULT_DEPARTMENT_NAMES,
        )
        for d in depts
    ]


@router.post("/departments", response_model=schemas.DepartmentOut)
def create_department(payload: schemas.DepartmentIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    slug = payload.slug.strip().lower().replace(" ", "-")
    name = payload.name.strip()
    if not slug or not name:
        raise HTTPException(status_code=400, detail="Both a slug and a display name are required")
    if db.query(models.Department).filter(models.Department.slug == slug).first():
        raise HTTPException(status_code=400, detail=f"A category with slug '{slug}' already exists")
    dept = models.Department(slug=slug, name=name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return schemas.DepartmentOut(slug=dept.slug, name=dept.name, count=0)


@router.delete("/departments/{slug}")
def delete_department(slug: str, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    dept = db.query(models.Department).filter(models.Department.slug == slug).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Category not found")
    in_use = db.query(models.Product).filter(models.Product.department == dept.name).count()
    if in_use:
        raise HTTPException(status_code=400, detail=f"Can't delete '{dept.name}' — {in_use} product(s) still use it. Move or delete those first.")
    db.delete(dept)
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------- brands --

@router.get("/brands", response_model=list[schemas.BrandOut])
def list_brands_admin(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    brands = db.query(models.Brand).all()
    return [
        schemas.BrandOut(
            id=b.id, slug=b.slug, name=b.name, logo_url=b.logo_url,
            count=db.query(models.Product).filter(models.Product.brand_id == b.id).count(),
        )
        for b in brands
    ]


@router.post("/brands", response_model=schemas.BrandOut)
def create_brand(payload: schemas.BrandIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    slug = payload.slug.strip().lower().replace(" ", "-")
    name = payload.name.strip()
    if not slug or not name:
        raise HTTPException(status_code=400, detail="Both a slug and a display name are required")
    if db.query(models.Brand).filter(models.Brand.slug == slug).first():
        raise HTTPException(status_code=400, detail=f"A brand with slug '{slug}' already exists")
    brand = models.Brand(slug=slug, name=name)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return schemas.BrandOut(id=brand.id, slug=brand.slug, name=brand.name, logo_url=None, count=0)


@router.post("/brands/{brand_id}/logo", response_model=schemas.BrandOut)
async def upload_brand_logo(brand_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if brand.logo_url:
        delete_image_by_url(db, brand.logo_url)
    content = await file.read()
    brand.logo_url = save_image_to_db(db, content, file.content_type)
    db.commit()
    db.refresh(brand)
    return schemas.BrandOut(
        id=brand.id, slug=brand.slug, name=brand.name, logo_url=brand.logo_url,
        count=db.query(models.Product).filter(models.Product.brand_id == brand.id).count(),
    )


@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    in_use = db.query(models.Product).filter(models.Product.brand_id == brand_id).count()
    if in_use:
        raise HTTPException(status_code=400, detail=f"Can't delete '{brand.name}' — {in_use} product(s) still use it. Move or delete those first.")
    if brand.logo_url:
        delete_image_by_url(db, brand.logo_url)
    db.delete(brand)
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------- delivery zones --

@router.get("/delivery-zones", response_model=list[schemas.DeliveryZoneOut])
def list_delivery_zones_admin(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    return db.query(models.DeliveryZone).order_by(models.DeliveryZone.sort_order).all()


@router.post("/delivery-zones", response_model=schemas.DeliveryZoneOut)
def create_delivery_zone(payload: schemas.DeliveryZoneIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="A zone name is required")
    if db.query(models.DeliveryZone).filter(models.DeliveryZone.name == name).first():
        raise HTTPException(status_code=400, detail=f"A delivery zone named '{name}' already exists")
    next_order = db.query(models.DeliveryZone).count()
    zone = models.DeliveryZone(name=name, fee=payload.fee, sort_order=next_order)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.patch("/delivery-zones/{zone_id}", response_model=schemas.DeliveryZoneOut)
def update_delivery_zone(zone_id: int, payload: schemas.DeliveryZoneUpdateIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    zone = db.query(models.DeliveryZone).filter(models.DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Delivery zone not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/delivery-zones/{zone_id}")
def delete_delivery_zone(zone_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    zone = db.query(models.DeliveryZone).filter(models.DeliveryZone.id == zone_id).first()
    if zone:
        db.delete(zone)
        db.commit()
    return {"ok": True}


# ----------------------------------------------------------- coupons --

@router.get("/coupons", response_model=list[schemas.CouponOut])
def list_coupons(db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    return db.query(models.Coupon).order_by(models.Coupon.created_at.desc()).all()


@router.post("/coupons", response_model=schemas.CouponOut)
def create_coupon(payload: schemas.CouponIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    code = payload.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="A coupon code is required")
    if payload.discount_type not in models.COUPON_DISCOUNT_TYPES:
        raise HTTPException(status_code=400, detail=f"discount_type must be one of {models.COUPON_DISCOUNT_TYPES}")
    if db.query(models.Coupon).filter(models.Coupon.code == code).first():
        raise HTTPException(status_code=400, detail=f"Coupon code '{code}' already exists")
    coupon = models.Coupon(
        code=code, discount_type=payload.discount_type, discount_value=payload.discount_value,
        min_order_value=payload.min_order_value, category_slug=payload.category_slug,
        department=payload.department, first_order_only=payload.first_order_only,
        usage_limit=payload.usage_limit, expires_at=payload.expires_at, is_active=True,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.patch("/coupons/{coupon_id}", response_model=schemas.CouponOut)
def update_coupon(coupon_id: int, payload: schemas.CouponUpdateIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    coupon = db.query(models.Coupon).filter(models.Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(coupon, field, value)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}")
def delete_coupon(coupon_id: int, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    coupon = db.query(models.Coupon).filter(models.Coupon.id == coupon_id).first()
    if coupon:
        db.delete(coupon)
        db.commit()
    return {"ok": True}


# ----------------------------------------------------------- subscribers / offers --

@router.get("/subscribers", response_model=list[schemas.SubscriberOut])
def list_subscribers(
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    admin: models.AdminUser = Depends(auth.get_current_admin),
):
    q = db.query(models.Subscriber)
    if start_date:
        q = q.filter(models.Subscriber.subscribed_at >= datetime.combine(start_date, time.min))
    if end_date:
        q = q.filter(models.Subscriber.subscribed_at <= datetime.combine(end_date, time.max))
    if category and category != "all":
        q = q.filter(models.Subscriber.category == category)
    return q.order_by(models.Subscriber.subscribed_at.desc()).all()


@router.post("/subscribers/send-offer")
def send_offer(payload: schemas.SendOfferIn, db: Session = Depends(get_db), admin: models.AdminUser = Depends(auth.get_current_admin)):
    if not payload.subscriber_ids:
        raise HTTPException(status_code=400, detail="Select at least one subscriber.")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Write a message to send.")

    subscribers = db.query(models.Subscriber).filter(models.Subscriber.id.in_(payload.subscriber_ids)).all()
    html = render_offer_email_html(payload.message.strip())
    sent, failed = 0, []
    for sub in subscribers:
        ok = send_simple_email(sub.email, payload.subject.strip() or "A message from TIME-X", html)
        if ok:
            sent += 1
        else:
            failed.append(sub.email)

    return {"requested": len(payload.subscriber_ids), "found": len(subscribers), "sent": sent, "failed": failed}
