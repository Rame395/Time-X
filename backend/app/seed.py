"""
Seeds the database on first run only (checks if any product already exists).
TIME-X is a premium watch seller in Nepal — every product below is placeholder
catalog data meant to demonstrate the full platform. Replace or edit any of
it freely from the admin panel once you have real product photography and
copy.
"""
import os
from pathlib import Path

from sqlalchemy.orm import Session

from . import models, config
from .image_utils import save_image_to_db
from .settings_utils import get_setting, set_setting
from .auth import hash_password


def _img(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?q=80&w=1200&auto=format&fit=crop"


# A small pool of verified watch photography, reused across the catalog —
# swap in real product photography via the admin panel whenever you're ready.
_BLUE_OMEGA = "1762708052123-7332966eaecb"
_SILVER_CHRONO = "1600003014608-c2ccc1570a65"
_GOLD_BLACK_ISOLATED = "1623998021450-85c29c644e0d"
_BREITLING_CHRONO = "1548171838-b3d4c18a3a67"
_WRIST_CHRONO = "1618215649872-6e3143a716ec"
_THREE_WATCHES = "1704783339057-3fb087d3bc98"

SIZES = ["36mm", "38mm", "40mm", "42mm", "44mm"]
STOCK_BY_SIZE = {"36mm": 8, "38mm": 14, "40mm": 22, "42mm": 18, "44mm": 10}


MEN_PRODUCTS = [
    dict(
        title="Sagarmatha Automatic", department="Automatic", subcategory="Heritage", price=45000,
        description="A self-winding automatic movement housed in a brushed stainless steel case, named for "
                     "the peak that watches over Kathmandu. Sapphire crystal front and back reveal the "
                     "hand-finished movement at work.",
        material="316L Stainless Steel, Sapphire Crystal, Genuine Leather Strap",
        collection_tag="heritage-collection", is_new_arrival=False, is_best_seller=True,
        images=[_BLUE_OMEGA, _SILVER_CHRONO, _THREE_WATCHES],
        colors=[("Midnight Black", "#111111"), ("Silver Steel", "#C0C0C0"), ("Slate Grey", "#4A4A4A")],
    ),
    dict(
        title="Thamel Chronograph", department="Chronograph", subcategory="Racing", price=52000, compare_at_price=61000,
        description="A tri-compax chronograph built for precision — tachymeter bezel, luminous hands, "
                     "and a case architecture engineered for legibility at a glance.",
        material="High-Tech Ceramic Bezel, Stainless Steel Case, Sapphire Crystal",
        collection_tag="chronograph-collection", is_new_arrival=True, is_best_seller=True,
        images=[_BREITLING_CHRONO, _WRIST_CHRONO],
        colors=[("Gunmetal", "#2C2C2E"), ("Ivory White", "#F5F5F0")],
    ),
    dict(
        title="Annapurna Diver", department="Diver", subcategory="Professional", price=58000,
        description="Water-resistant to 300m with a unidirectional rotating bezel and a case built to take "
                     "on altitude and depth alike. Built for those who move between the mountains and the sea.",
        material="Titanium Case, Ceramic Bezel, Rubber Strap",
        collection_tag="", is_new_arrival=False, is_best_seller=True,
        images=[_SILVER_CHRONO, _BREITLING_CHRONO],
        colors=[("Deep Black", "#0A0A0A")],
    ),
    dict(
        title="Kathmandu Skeleton", department="Automatic", subcategory="Skeleton", price=68000, compare_at_price=78000,
        description="An open-worked dial exposes the full automatic movement in motion — every gear and "
                     "escapement visible through a sapphire crystal front and case back.",
        material="Stainless Steel, Open-Worked Dial, Sapphire Crystal",
        collection_tag="heritage-collection", is_new_arrival=False,
        images=[_THREE_WATCHES, _GOLD_BLACK_ISOLATED],
        colors=[("Silver Steel", "#C0C0C0")],
    ),
    dict(
        title="Everest Base Classic", department="Classic", subcategory="Minimalist", price=32000,
        description="A dress watch stripped to its essentials — a clean dial, slim profile, and a "
                     "hand-stitched leather strap for a silhouette that disappears under a cuff.",
        material="Stainless Steel, Domed Mineral Crystal, Leather Strap",
        collection_tag="", is_new_arrival=False,
        images=[_GOLD_BLACK_ISOLATED, _WRIST_CHRONO],
        colors=[("Midnight Black", "#111111"), ("Ivory White", "#F5F5F0")],
    ),
    dict(
        title="Lukla Field Chronograph", department="Chronograph", subcategory="Pilot", price=49500,
        description="Pilot-inspired legibility with a bidirectional bezel and oversized crown built for "
                     "use with gloves on. Named for the runway that opens the way to the highest peaks.",
        material="Stainless Steel, Anti-Reflective Sapphire Crystal",
        collection_tag="chronograph-collection", is_new_arrival=False,
        images=[_WRIST_CHRONO, _BREITLING_CHRONO],
        colors=[("Slate Grey", "#4A4A4A"), ("Gunmetal", "#2C2C2E")],
    ),
    dict(
        title="Pokhara Open Heart", department="Automatic", subcategory="Open Heart", price=41000,
        description="A cut-away dial reveals the balance wheel in constant motion — a quiet detail for "
                     "those who know exactly what they're looking at.",
        material="Stainless Steel, Open Heart Dial, Sapphire Crystal",
        collection_tag="", is_new_arrival=False,
        images=[_BLUE_OMEGA, _THREE_WATCHES],
        colors=[("Silver Steel", "#C0C0C0")],
    ),
    dict(
        title="Kathmandu Digital Sport", department="Digital", subcategory="Multi-Function", price=18500,
        description="A rugged digital sport watch with an LCD display, backlit face, stopwatch, and dual "
                     "time zones — built for the trail as much as the daily commute.",
        material="Resin Case, Digital LCD Display, Silicone Strap",
        collection_tag="", is_new_arrival=True,
        images=[_THREE_WATCHES, _WRIST_CHRONO],
        colors=[("Midnight Black", "#111111"), ("Gunmetal", "#2C2C2E")],
    ),
]


WOMEN_PRODUCTS = [
    dict(
        title="Petite Automatic", department="Automatic", subcategory="Heritage", price=42000,
        description="A smaller-cased automatic built with the same movement architecture as our men's "
                     "line, finished with a refined dial and a slimmer bracelet fit.",
        material="316L Stainless Steel, Sapphire Crystal, Steel Bracelet",
        collection_tag="heritage-collection", is_new_arrival=False,
        images=[_SILVER_CHRONO, _GOLD_BLACK_ISOLATED],
        colors=[("Ivory White", "#F5F5F0"), ("Silver Steel", "#C0C0C0")],
    ),
    dict(
        title="Kathmandu Classic Petite", department="Classic", subcategory="Minimalist", price=29500,
        description="A quiet, clean-faced dress watch with a domed crystal and a hand-stitched leather "
                     "strap — designed to be worn every day without a second thought.",
        material="Stainless Steel, Domed Mineral Crystal, Leather Strap",
        collection_tag="", is_new_arrival=False,
        images=[_GOLD_BLACK_ISOLATED, _THREE_WATCHES],
        colors=[("Midnight Black", "#111111"), ("Ivory White", "#F5F5F0")],
    ),
    dict(
        title="Annapurna Diver Petite", department="Diver", subcategory="Professional", price=54000,
        description="The same 300m water resistance and ceramic bezel as our men's diver, cased down for "
                     "a slimmer wrist without losing any of the durability.",
        material="Titanium Case, Ceramic Bezel, Rubber Strap",
        collection_tag="", is_new_arrival=False,
        images=[_BREITLING_CHRONO, _SILVER_CHRONO],
        colors=[("Deep Black", "#0A0A0A"), ("Silver Steel", "#C0C0C0")],
    ),
    dict(
        title="Pokhara Lake Chronograph", department="Chronograph", subcategory="Racing", price=47500,
        compare_at_price=55000,
        description="A tri-compax chronograph in a refined case, finished with a mother-of-pearl-effect "
                     "dial and a steel bracelet built to catch the light.",
        material="Stainless Steel, Sapphire Crystal, Steel Bracelet",
        collection_tag="chronograph-collection", is_new_arrival=False, is_best_seller=True,
        images=[_WRIST_CHRONO, _BLUE_OMEGA],
        colors=[("Gunmetal", "#2C2C2E"), ("Silver Steel", "#C0C0C0")],
    ),
    dict(
        title="Lumbini Open Heart", department="Automatic", subcategory="Open Heart", price=38500,
        description="An open-worked heart at the dial's center, framed by a slim polished case and a "
                     "supple leather strap.",
        material="Stainless Steel, Open Heart Dial, Leather Strap",
        collection_tag="", is_new_arrival=True,
        images=[_THREE_WATCHES, _GOLD_BLACK_ISOLATED],
        colors=[("Ivory White", "#F5F5F0")],
    ),
    dict(
        title="Lumbini Digital Petite", department="Digital", subcategory="Multi-Function", price=15500,
        description="A slim digital watch with a soft-glow display, daily alarm, and a lightweight silicone "
                     "strap — everyday convenience with none of the bulk.",
        material="Resin Case, Digital LCD Display, Silicone Strap",
        collection_tag="", is_new_arrival=True,
        images=[_GOLD_BLACK_ISOLATED, _THREE_WATCHES],
        colors=[("Ivory White", "#F5F5F0"), ("Midnight Black", "#111111")],
    ),
]


def _derive_specs(item: dict) -> dict:
    """Fills in the watch-spec fields from what the product copy already says,
    rather than requiring every field to be typed out per product. Admin can
    always correct any of these from the product edit form afterward."""
    text = (item["material"] + " " + item["description"]).lower()
    dept = item.get("department", "Classic")

    movement = {"Automatic": "Automatic", "Chronograph": "Chronograph", "Diver": "Automatic", "Digital": "Digital"}.get(dept, "Quartz")
    case_material = "Titanium" if "titanium" in text else ("Ceramic" if "ceramic case" in text else "Stainless Steel")
    glass_type = "Sapphire Crystal" if "sapphire" in text else "Mineral Crystal"
    strap_material = "Leather" if "leather" in text else ("Rubber" if "rubber" in text else ("Steel Bracelet" if "bracelet" in text else "Leather"))
    water_resistance = "300m" if "300m" in text else ("100m" if "diver" in dept.lower() else "50m")
    dial_color = item["colors"][0][0] if item.get("colors") else "Black"

    return dict(
        movement=movement, case_material=case_material, glass_type=glass_type,
        strap_material=strap_material, water_resistance=water_resistance,
        dial_color=dial_color, warranty="2 Years",
    )


def _create_products(db: Session, category: models.Category, items: list[dict], brand: "models.Brand") -> None:
    for item in items:
        specs = _derive_specs(item)
        slug = _slugify(item["title"])
        product = models.Product(
            slug=slug,
            title=item["title"], category_id=category.id,
            department=item.get("department", "Classic"),
            subcategory=item["subcategory"], price=item["price"],
            compare_at_price=item.get("compare_at_price"),
            description=item["description"], material=item["material"],
            collection_tag=item["collection_tag"], is_new_arrival=item["is_new_arrival"],
            is_best_seller=item.get("is_best_seller", False),
            is_featured=item.get("is_featured", False),
            is_limited_edition=item.get("is_limited_edition", False),
            is_active=True,
            brand_id=brand.id, model_name=item["title"],
            reference_number=f"REF-{slug[:8].upper()}", sku=f"TN-{slug[:10].upper()}",
            condition="new",
            **specs,
        )
        db.add(product)
        db.flush()

        for order, photo_id in enumerate(item["images"]):
            db.add(models.ProductImage(product_id=product.id, url=_img(photo_id), sort_order=order))

        for color_name, hex_code in item["colors"]:
            db.add(models.ProductColor(product_id=product.id, name=color_name, hex_code=hex_code))
            for size in item.get("sizes", SIZES):
                db.add(models.ProductVariant(
                    product_id=product.id, size=size, color_name=color_name,
                    strap_material=specs["strap_material"],
                    sku=f"TN-{slug[:8].upper()}-{color_name[:3].upper()}-{size}",
                    stock_qty=STOCK_BY_SIZE.get(size, 15),
                ))


def _slugify(title: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def ensure_unisex_category(db: Session) -> None:
    """Runs on every startup (not just first seed) so existing databases pick up
    the Unisex category too, without needing a full re-seed or migration tool."""
    if not db.query(models.Category).filter(models.Category.slug == "unisex").first():
        db.add(models.Category(slug="unisex", name="Unisex"))
        db.commit()


DEFAULT_DEPARTMENTS = [("automatic", "Automatic"), ("chronograph", "Chronograph"), ("classic", "Classic"), ("diver", "Diver"), ("digital", "Digital")]


def ensure_default_departments(db: Session) -> None:
    """Same pattern as ensure_unisex_category — runs every startup so existing
    databases get any newly-added default department without a full re-seed."""
    existing_slugs = {d.slug for d in db.query(models.Department).all()}
    added = False
    for slug, name in DEFAULT_DEPARTMENTS:
        if slug not in existing_slugs:
            db.add(models.Department(slug=slug, name=name))
            added = True
    if added:
        db.commit()


DEFAULT_DELIVERY_ZONES = [
    ("Kathmandu", 100), ("Lalitpur", 100), ("Bhaktapur", 120),
    ("Butwal", 150), ("Pokhara", 180), ("Other Districts", 250),
]


def ensure_default_delivery_zones(db: Session) -> None:
    """Same runs-every-startup pattern as the other ensure_* helpers."""
    if db.query(models.DeliveryZone).first():
        return
    for order, (name, fee) in enumerate(DEFAULT_DELIVERY_ZONES):
        db.add(models.DeliveryZone(name=name, fee=fee, sort_order=order))
    db.commit()


ASSETS_DIR = Path(__file__).parent / "assets"


def ensure_default_brand_assets(db: Session) -> None:
    """Loads the bundled logo and brand-showcase images into the database on
    any fresh install — same runs-every-startup pattern as the other ensure_*
    helpers, so a freshly-seeded database always has these ready without
    requiring a manual admin upload first. Admin can replace either at any
    time from Settings; once site_logo_path/brand_showcase_path is set to
    something, this function no longer overwrites it.
    """
    if not get_setting(db, "site_logo_path", ""):
        logo_file = ASSETS_DIR / "logo-timex-nepal-gold.png"
        if logo_file.exists():
            content = logo_file.read_bytes()
            url = save_image_to_db(db, content, "image/png")
            set_setting(db, "site_logo_path", url)

    if not get_setting(db, "brand_showcase_path", ""):
        showcase_file = ASSETS_DIR / "brand_showcase.png"
        if showcase_file.exists():
            content = showcase_file.read_bytes()
            url = save_image_to_db(db, content, "image/png")
            set_setting(db, "brand_showcase_path", url)

    db.commit()


CARRIED_BRANDS = [
    ("lacoste", "Lacoste", "lacoste.png"),
    ("calvin-klein", "Calvin Klein", "calvin-klein.png"),
    ("guess", "Guess", "guess.png"),
    ("tommy-hilfiger", "Tommy Hilfiger", "tommy-hilfiger.png"),
    ("lee-cooper", "Lee Cooper", "lee-cooper.png"),
    ("timex", "Timex", "timex.png"),
]


def ensure_carried_brands(db: Session) -> None:
    """The 6 established watch brands TIME-X carries alongside its own house
    brand — shown as a clickable logo row on the homepage and selectable on
    the product form. Runs every startup so any missing brand (e.g. one
    added to CARRIED_BRANDS after initial seeding) gets created without a
    full re-seed. Never overwrites a brand admin has already edited."""
    existing_slugs = {b.slug for b in db.query(models.Brand).all()}
    for slug, name, filename in CARRIED_BRANDS:
        if slug in existing_slugs:
            continue
        logo_file = ASSETS_DIR / "brands" / filename
        logo_url = None
        if logo_file.exists():
            logo_url = save_image_to_db(db, logo_file.read_bytes(), "image/png")
        db.add(models.Brand(slug=slug, name=name, logo_url=logo_url))
    db.commit()


def seed_if_empty(db: Session) -> None:
    if db.query(models.Product).first():
        return  # already seeded

    men = models.Category(slug="men", name="Men")
    women = models.Category(slug="women", name="Women")
    unisex = models.Category(slug="unisex", name="Unisex")
    db.add_all([men, women, unisex])
    for slug, name in DEFAULT_DEPARTMENTS:
        db.add(models.Department(slug=slug, name=name))
    db.flush()
    ensure_default_delivery_zones(db)

    house_brand = models.Brand(slug="timex-nepal", name="TIME-X")
    db.add(house_brand)
    db.flush()

    _create_products(db, men, MEN_PRODUCTS, house_brand)
    _create_products(db, women, WOMEN_PRODUCTS, house_brand)

    db.add(models.Coupon(
        code="WELCOME10", discount_type="percentage", discount_value=10,
        min_order_value=5000, first_order_only=True, is_active=True,
    ))

    if not db.query(models.AdminUser).first():
        db.add(models.AdminUser(
            username=config.DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(config.DEFAULT_ADMIN_PASSWORD),
        ))

    default_settings = {
        "whatsapp_number": config.WHATSAPP_DEFAULT,
        "merchant_name": "TIME-X TIMEPIECES",
        "merchant_number": "",
        "qr_image_path": "",
        "cod_enabled": "true",
        "mobile_banking_enabled": "true",
        "contact_phone": config.WHATSAPP_DEFAULT,
        "instagram_url": "",
        "tiktok_url": "",
        "free_delivery_enabled": "true",
        "free_delivery_threshold": "5000",
    }
    for key, value in default_settings.items():
        db.add(models.SiteSetting(key=key, value=value))

    db.commit()

def ensure_display_rank_column(db: Session):
    from sqlalchemy import text
    try:
        db.execute(text("SELECT display_rank FROM products LIMIT 1"))
    except Exception:
        db.rollback()
        try:
            db.execute(text("ALTER TABLE products ADD COLUMN display_rank INTEGER DEFAULT 0;"))
            db.commit()
            print("Added display_rank column to products table.")
        except Exception as e:
            db.rollback()
            print(f"Could not add display_rank column: {e}")
