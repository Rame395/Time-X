from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func

from .. import models, schemas, config, nepal_geo
from ..cache_utils import cache_get, cache_set, invalidate_catalog_cache
from ..database import get_db, SessionLocal
from ..image_utils import get_cached_image_file, write_image_cache, optimize_image_bytes
from ..settings_utils import get_all_settings

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/media/image/{image_id}")
def get_image(image_id: int, w: Optional[int] = Query(None, ge=100, le=2000)):
    target_w = 480 if (w is not None and w <= 540) else (800 if (w is not None and w <= 900) else None)

    cached = get_cached_image_file(image_id, target_w)
    if cached:
        bin_path, content_type = cached
        return FileResponse(
            bin_path,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    # For thumbnail requests, try generating from already-cached full-size file without touching DB.
    if target_w is not None:
        base_cached = get_cached_image_file(image_id, None)
        if base_cached:
            base_bin, base_ct = base_cached
            try:
                with open(base_bin, "rb") as f:
                    base_bytes = f.read()
                thumb_bytes, thumb_ct = optimize_image_bytes(base_bytes, base_ct, max_width=target_w, quality=80)
                bin_path = write_image_cache(image_id, thumb_bytes, thumb_ct, target_w)
                return FileResponse(
                    bin_path,
                    media_type=thumb_ct,
                    headers={"Cache-Control": "public, max-age=31536000, immutable"},
                )
            except OSError:
                pass

    db = SessionLocal()
    try:
        image = db.query(models.Image).filter(models.Image.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        data = image.data
        content_type = image.content_type or "image/jpeg"
    finally:
        db.close()

    # Lazily optimize oversized legacy images on first miss before caching to disk.
    if content_type.startswith("image/") and len(data) > 100_000:
        data, content_type = optimize_image_bytes(data, content_type)

    try:
        base_bin = write_image_cache(image_id, data, content_type, None)
        if target_w is not None and content_type.startswith("image/"):
            thumb_bytes, thumb_ct = optimize_image_bytes(data, content_type, max_width=target_w, quality=80)
            thumb_bin = write_image_cache(image_id, thumb_bytes, thumb_ct, target_w)
            return FileResponse(
                thumb_bin,
                media_type=thumb_ct,
                headers={"Cache-Control": "public, max-age=31536000, immutable"},
            )
        return FileResponse(
            base_bin,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )
    except OSError:
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )


@router.post("/subscribe", response_model=schemas.SubscriberOut)
def subscribe(payload: schemas.SubscriberIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    category = payload.category if payload.category in models.SUBSCRIBER_CATEGORIES else "all"

    existing = db.query(models.Subscriber).filter(models.Subscriber.email == email).first()
    if existing:
        existing.category = category  # resubscribing updates their stated interest
        db.commit()
        db.refresh(existing)
        return existing

    sub = models.Subscriber(email=email, category=category)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/nepal-locations")
def get_nepal_locations():
    """Province -> District list, single source of truth shared with server-side validation."""
    return nepal_geo.NEPAL_PROVINCES


@router.get("/site-images", response_model=dict[str, list[schemas.SiteImageOut]])
def get_active_site_images_batch(
    response: Response,
    slots: Optional[str] = Query(None, description="Comma-separated slot names"),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    slot_list = [s.strip() for s in slots.split(",") if s.strip()] if slots else []
    cache_key = f"site_images:{','.join(sorted(slot_list)) if slot_list else '*'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    q = db.query(models.SiteImage).filter(models.SiteImage.is_active == True)  # noqa: E712
    if slot_list:
        q = q.filter(models.SiteImage.slot.in_(slot_list))
    rows = q.order_by(models.SiteImage.sort_order).all()
    grouped: dict[str, list[schemas.SiteImageOut]] = {s: [] for s in slot_list}
    for row in rows:
        grouped.setdefault(row.slot, []).append(schemas.SiteImageOut.model_validate(row))
    cache_set(cache_key, grouped, ttl=300.0)
    return grouped


@router.get("/site-images/{slot}", response_model=list[schemas.SiteImageOut])
def get_active_site_images(slot: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=60"
    cache_key = f"site_image:{slot}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    rows = (
        db.query(models.SiteImage)
        .filter(models.SiteImage.slot == slot, models.SiteImage.is_active == True)  # noqa: E712
        .order_by(models.SiteImage.sort_order)
        .all()
    )
    out = [schemas.SiteImageOut.model_validate(r) for r in rows]
    cache_set(cache_key, out, ttl=300.0)
    return out


@router.get("/settings", response_model=schemas.PublicSettingsOut)
def get_public_settings(response: Response, db: Session = Depends(get_db)):
    """Storefront-facing settings: WhatsApp number, payment QR, which payment methods are on."""
    s = get_all_settings(db)
    response.headers["Cache-Control"] = "public, max-age=60"
    default_qr = s.get("qr_image_path", "")
    return schemas.PublicSettingsOut(
        whatsapp_number=s.get("whatsapp_number") or config.WHATSAPP_DEFAULT,
        merchant_name=s.get("merchant_name") or "TIME-X",
        merchant_number=s.get("merchant_number", ""),
        qr_image_url=default_qr or None,
        qr_images_by_method={
            method: s.get(f"qr_image_path_{method}", "") or default_qr or None
            for method in ("esewa", "khalti", "fonepay", "connectips", "bank_transfer")
        },
        site_logo_url=s.get("site_logo_path", "") or None,
        brand_showcase_url=s.get("brand_showcase_path", "") or None,
        site_brand_name=s.get("site_brand_name") or "TIME-X",
        site_tagline=s.get("site_tagline") or "Precision, crafted. Timeless. Premium watches from Kathmandu.",
        cod_enabled=s.get("cod_enabled", "true") == "true",
        mobile_banking_enabled=s.get("mobile_banking_enabled", "true") == "true",
        contact_phone=s.get("contact_phone") or config.WHATSAPP_DEFAULT,
        instagram_url=s.get("instagram_url", ""),
        tiktok_url=s.get("tiktok_url", ""),
        free_delivery_enabled=s.get("free_delivery_enabled", "false") == "true",
        free_delivery_threshold=int(s.get("free_delivery_threshold") or "5000"),
    )


def _card_from_product(p: models.Product) -> schemas.ProductCardOut:
    imgs = sorted(p.images, key=lambda i: i.sort_order)
    return schemas.ProductCardOut(
        id=p.id, slug=p.slug, title=p.title, price=p.price, compare_at_price=p.compare_at_price,
        department=p.department or "Classic", subcategory=p.subcategory or "", category_slug=p.category.slug,
        is_new_arrival=p.is_new_arrival, is_best_seller=p.is_best_seller, is_featured=p.is_featured,
        is_limited_edition=p.is_limited_edition, collection_tag=p.collection_tag or "",
        display_rank=p.display_rank,
        brand_name=p.brand.name if p.brand else None, movement=p.movement or "",
        case_material=p.case_material or "", dial_color=p.dial_color or "",
        in_stock=any(v.stock_qty > 0 for v in p.variants) if p.variants else True,
        available_sizes=sorted({v.size for v in p.variants if v.size}),
        available_straps=sorted({v.strap_material for v in p.variants if v.strap_material}),
        primary_image=imgs[0].url if len(imgs) > 0 else None,
        secondary_image=imgs[1].url if len(imgs) > 1 else None,
        video_url=p.video_url,
    )


@router.get("/brands", response_model=list[schemas.BrandOut])
def list_brands(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=60"
    cached = cache_get("brands")
    if cached is not None:
        return cached
    brands = db.query(models.Brand).all()
    counts = dict(
        db.query(models.Product.brand_id, func.count(models.Product.id))
        .filter(models.Product.is_active == True)  # noqa: E712
        .group_by(models.Product.brand_id)
        .all()
    )
    out = [
        schemas.BrandOut(
            id=b.id, slug=b.slug, name=b.name, logo_url=b.logo_url,
            count=counts.get(b.id, 0),
        )
        for b in brands
    ]
    cache_set("brands", out, ttl=300.0)
    return out


HOMEPAGE_SLOTS = (
    "homepage_hero,homepage_hero_video,homepage_story,"
    "homepage_tile_men,homepage_tile_women,homepage_tile_new,instagram_grid"
)


@router.get("/homepage")
def get_homepage_bundle(response: Response, db: Session = Depends(get_db)):
    """Single cached bootstrap payload for the homepage — avoids 6+ separate requests."""
    response.headers["Cache-Control"] = "public, max-age=60"
    cached = cache_get("homepage")
    if cached is not None:
        return cached

    dummy_resp = Response()
    payload = {
        "settings": get_public_settings(dummy_resp, db).model_dump(),
        "brands": [b.model_dump() for b in list_brands(dummy_resp, db)],
        "site_images": {
            slot: [img.model_dump() for img in imgs]
            for slot, imgs in get_active_site_images_batch(dummy_resp, HOMEPAGE_SLOTS, db).items()
        },
        "featured": [
            c.model_dump()
            for c in list_products(dummy_resp, is_featured=True, brand=None, in_stock=None, limit=4, offset=0, db=db)
        ],
        "on_sale": [
            c.model_dump()
            for c in list_products(dummy_resp, on_sale=True, brand=None, in_stock=None, limit=4, offset=0, db=db)
        ],
        "best_sellers": [
            c.model_dump()
            for c in list_products(dummy_resp, is_best_seller=True, sort="popularity", brand=None, in_stock=None, limit=4, offset=0, db=db)
        ],
    }
    cache_set("homepage", payload, ttl=300.0)
    return payload


@router.get("/delivery-zones", response_model=list[schemas.DeliveryZoneOut])
def list_delivery_zones(db: Session = Depends(get_db)):
    return (
        db.query(models.DeliveryZone)
        .filter(models.DeliveryZone.is_active == True)  # noqa: E712
        .order_by(models.DeliveryZone.sort_order)
        .all()
    )


@router.post("/coupons/apply", response_model=schemas.CouponApplyOut)
def apply_coupon(payload: schemas.CouponApplyIn, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    coupon = db.query(models.Coupon).filter(models.Coupon.code == payload.code.strip().upper()).first()
    if not coupon or not coupon.is_active:
        return schemas.CouponApplyOut(valid=False, message="This coupon code isn't valid.")
    if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
        return schemas.CouponApplyOut(valid=False, message="This coupon has expired.")
    if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
        return schemas.CouponApplyOut(valid=False, message="This coupon has reached its usage limit.")
    if coupon.first_order_only:
        email = (payload.email or "").strip()
        is_first_order = not email or not db.query(models.Order).filter(models.Order.email == email).first()
        if not is_first_order:
            return schemas.CouponApplyOut(valid=False, message="This coupon is only valid on your first order.")
    if payload.subtotal < coupon.min_order_value:
        return schemas.CouponApplyOut(valid=False, message=f"Minimum order of NPR {coupon.min_order_value:,} required for this coupon.")

    discount = (
        round(payload.subtotal * coupon.discount_value / 100)
        if coupon.discount_type == "percentage"
        else min(coupon.discount_value, payload.subtotal)
    )
    return schemas.CouponApplyOut(valid=True, discount_amount=discount, message=f"Coupon applied — NPR {discount:,} off.")


@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(models.Category).all()
    out = []
    for c in cats:
        count = db.query(func.count(models.Product.id)).filter(
            models.Product.category_id == c.id, models.Product.is_active == True  # noqa: E712
        ).scalar()
        out.append(schemas.CategoryOut(slug=c.slug, name=c.name, count=count))
    return out


@router.get("/products/taxonomy")
def get_taxonomy(category: str, db: Session = Depends(get_db)):
    """Department -> [subcategories] for the mega-menu, built live from whatever
    products actually exist — so a new department or subcategory just shows up,
    no code change needed. `category` is the gender slug (men/women)."""
    allowed_slugs = [category, "unisex"] if category in ("men", "women") else [category]
    rows = (
        db.query(models.Product.department, models.Product.subcategory)
        .join(models.Category)
        .filter(models.Category.slug.in_(allowed_slugs), models.Product.is_active == True)  # noqa: E712
        .distinct()
        .all()
    )
    taxonomy: dict[str, list[str]] = {}
    for department, subcategory in rows:
        department = department or "Clothing"
        if not subcategory:
            continue
        taxonomy.setdefault(department, [])
        if subcategory not in taxonomy[department]:
            taxonomy[department].append(subcategory)
    for department in taxonomy:
        taxonomy[department].sort()
    return taxonomy


@router.get("/products", response_model=list[schemas.ProductCardOut])
def list_products(
    response: Response,
    category: Optional[str] = None,
    department: Optional[str] = None,
    subcategory: Optional[str] = None,
    is_new_arrival: Optional[bool] = None,
    on_sale: Optional[bool] = None,
    collection: Optional[str] = None,
    size: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    search: Optional[str] = None,
    brand: Optional[str] = Query(None, description="brand slug"),
    movement: Optional[str] = None,
    strap_material: Optional[str] = None,
    case_material: Optional[str] = None,
    dial_color: Optional[str] = None,
    in_stock: Optional[bool] = Query(None, description="true = only items with stock in at least one variant"),
    is_best_seller: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    is_limited_edition: Optional[bool] = None,
    sort: Optional[str] = Query(None, description="price_asc | price_desc | latest | popularity"),
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    cache_key = (
        f"products:{category}:{department}:{subcategory}:{is_new_arrival}:{on_sale}:"
        f"{collection}:{size}:{min_price}:{max_price}:{(search or '').strip().lower()}:"
        f"{brand}:{movement}:{strap_material}:{case_material}:{dial_color}:"
        f"{in_stock}:{is_best_seller}:{is_featured}:{is_limited_edition}:{sort}:{limit}:{offset}"
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    q = (
        db.query(models.Product)
        .join(models.Category)
        .options(
            selectinload(models.Product.images),
            joinedload(models.Product.category),
            joinedload(models.Product.brand),
            selectinload(models.Product.variants),
        )
        .filter(models.Product.is_active == True)  # noqa: E712
    )
    if category:
        allowed_slugs = [category, "unisex"] if category in ("men", "women") else [category]
        q = q.filter(models.Category.slug.in_(allowed_slugs))
    if department:
        q = q.filter(models.Product.department == department)
    if subcategory:
        q = q.filter(models.Product.subcategory == subcategory)
    if is_new_arrival is not None:
        q = q.filter(models.Product.is_new_arrival == is_new_arrival)
    if is_best_seller is not None:
        q = q.filter(models.Product.is_best_seller == is_best_seller)
    if is_featured is not None:
        q = q.filter(models.Product.is_featured == is_featured)
    if is_limited_edition is not None:
        q = q.filter(models.Product.is_limited_edition == is_limited_edition)
    if on_sale:
        q = q.filter(models.Product.compare_at_price.isnot(None), models.Product.compare_at_price > models.Product.price)
    if collection:
        q = q.filter(models.Product.collection_tag == collection)
    if min_price is not None:
        q = q.filter(models.Product.price >= min_price)
    if max_price is not None:
        q = q.filter(models.Product.price <= max_price)
    if brand:
        q = q.join(models.Brand).filter(models.Brand.slug == brand)
    if movement:
        q = q.filter(models.Product.movement == movement)
    if case_material:
        q = q.filter(models.Product.case_material == case_material)
    if dial_color:
        q = q.filter(models.Product.dial_color == dial_color)
    if size or strap_material or in_stock is not None:
        q = q.join(models.ProductVariant)
        if size:
            q = q.filter(models.ProductVariant.size == size)
        if strap_material:
            q = q.filter(models.ProductVariant.strap_material == strap_material)
        if in_stock:
            q = q.filter(models.ProductVariant.stock_qty > 0)
    _search_term = None
    if search:
        q = q.outerjoin(models.Brand)
        _search_term = search.strip()
        like = f"%{_search_term}%"
        q = q.filter(
            (models.Product.title.ilike(like))
            | (models.Product.subcategory.ilike(like))
            | (models.Product.department.ilike(like))
            | (models.Product.description.ilike(like))
            | (models.Brand.name.ilike(like))
        )

    if sort == "price_asc":
        q = q.order_by(models.Product.price.asc())
    elif sort == "price_desc":
        q = q.order_by(models.Product.price.desc())
    elif sort == "popularity":
        q = q.order_by(models.Product.display_rank.asc(), models.Product.is_best_seller.desc(), models.Product.created_at.desc())
    else:
        q = q.order_by(models.Product.display_rank.asc(), models.Product.created_at.desc())

    q = q.distinct()
    if not _search_term:
        if offset:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)

    products = q.all()
    cards = [_card_from_product(p) for p in products]

    # Relevance sorting: prefix matches first, then contains matches
    if _search_term:
        term_lower = _search_term.lower()

        def _relevance(c):
            title = (c.title or "").lower()
            brand = (c.brand_name or "").lower()
            if title.startswith(term_lower):
                return 0
            if brand.startswith(term_lower):
                return 1
            if term_lower in title:
                return 2
            return 3

        cards.sort(key=_relevance)
        if limit is not None:
            cards = cards[offset : offset + limit]
        elif offset:
            cards = cards[offset:]

    cache_set(cache_key, cards, ttl=120.0 if _search_term else 300.0)
    return cards


@router.get("/products/{slug}", response_model=schemas.ProductDetailOut)
def get_product(slug: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=60"
    cache_key = f"product:{slug}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    p = (
        db.query(models.Product)
        .options(
            selectinload(models.Product.images),
            selectinload(models.Product.colors),
            selectinload(models.Product.variants),
            joinedload(models.Product.category),
            joinedload(models.Product.brand),
        )
        .filter(models.Product.slug == slug, models.Product.is_active == True)  # noqa: E712
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    visible_reviews = db.query(models.Review).filter(
        models.Review.product_id == p.id, models.Review.is_visible == True  # noqa: E712
    ).all()
    avg_rating = round(sum(r.rating for r in visible_reviews) / len(visible_reviews), 1) if visible_reviews else None
    out = schemas.ProductDetailOut(
        id=p.id, slug=p.slug, title=p.title, price=p.price, compare_at_price=p.compare_at_price,
        description=p.description or "", material=p.material or "",
        department=p.department or "Classic", subcategory=p.subcategory or "", category_slug=p.category.slug,
        collection_tag=p.collection_tag or "", is_new_arrival=p.is_new_arrival,
        is_best_seller=p.is_best_seller, is_featured=p.is_featured, is_limited_edition=p.is_limited_edition,
        display_rank=p.display_rank,
        brand_id=p.brand_id, brand_name=p.brand.name if p.brand else None,
        model_name=p.model_name or "", reference_number=p.reference_number or "", sku=p.sku or "",
        movement=p.movement or "", case_material=p.case_material or "", dial_color=p.dial_color or "",
        strap_material=p.strap_material or "", water_resistance=p.water_resistance or "",
        glass_type=p.glass_type or "", warranty=p.warranty or "", condition=p.condition or "new",
        has_certificate=p.has_certificate, video_url=p.video_url,
        images=[schemas.ImageOut.model_validate(i) for i in sorted(p.images, key=lambda i: i.sort_order)],
        colors=[schemas.ColorOut.model_validate(c) for c in p.colors],
        variants=[schemas.VariantOut.model_validate(v) for v in p.variants],
        avg_rating=avg_rating, review_count=len(visible_reviews),
    )
    cache_set(cache_key, out, ttl=300.0)
    return out


@router.get("/products/{slug}/reviews", response_model=list[schemas.ReviewOut])
def get_product_reviews(slug: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    reviews = (
        db.query(models.Review)
        .filter(models.Review.product_id == product.id, models.Review.is_visible == True)  # noqa: E712
        .order_by(models.Review.created_at.desc())
        .all()
    )
    return [schemas.ReviewOut.from_model(r) for r in reviews]


@router.post("/products/{slug}/reviews", response_model=schemas.ReviewOut)
def create_product_review(slug: str, payload: schemas.ReviewIn, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    if not payload.customer_name.strip():
        raise HTTPException(status_code=400, detail="Please enter your name")

    # Verified Purchase: only if the given order number is real AND actually contains
    # this product — otherwise the review still goes through, just unverified.
    order_id = None
    if payload.order_number.strip():
        order = db.query(models.Order).filter(models.Order.order_number == payload.order_number.strip().upper()).first()
        if order and any(i.product_id == product.id for i in order.items):
            order_id = order.id

    review = models.Review(
        product_id=product.id, order_id=order_id, customer_name=payload.customer_name.strip(),
        rating=payload.rating, comment=payload.comment.strip(), is_visible=True,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    invalidate_catalog_cache()
    return schemas.ReviewOut.from_model(review)


