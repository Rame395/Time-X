import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import models, schemas, config
from ..database import get_db
from ..auth import hash_password, verify_password

router = APIRouter(prefix="/api", tags=["customers"])


# ----------------------------------------------------------- auth helpers --

def _create_customer_session(db: Session, customer_id: int) -> str:
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=config.CUSTOMER_SESSION_TTL_DAYS)
    db.add(models.CustomerSession(token=token, customer_id=customer_id, expires_at=expires))
    db.commit()
    return token


def get_current_customer(request: Request, db: Session = Depends(get_db)) -> models.Customer:
    """Hard-required auth — raises 401 if not logged in. Use for endpoints that
    only make sense with an account (profile, addresses, order history)."""
    token = request.cookies.get(config.CUSTOMER_SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    session = db.query(models.CustomerSession).filter(models.CustomerSession.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Not signed in")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")
    customer = db.query(models.Customer).filter(models.Customer.id == session.customer_id).first()
    if not customer:
        raise HTTPException(status_code=401, detail="Not signed in")
    return customer


def get_optional_customer(request: Request, db: Session = Depends(get_db)) -> models.Customer | None:
    """Soft auth — returns None instead of raising, for endpoints (wishlist)
    that work for both guests and signed-in customers."""
    token = request.cookies.get(config.CUSTOMER_SESSION_COOKIE_NAME)
    if not token:
        return None
    session = db.query(models.CustomerSession).filter(models.CustomerSession.token == token).first()
    if not session:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return db.query(models.Customer).filter(models.Customer.id == session.customer_id).first()


def _get_or_create_wishlist_guest_token(request: Request, response: Response) -> str:
    token = request.cookies.get(config.WISHLIST_COOKIE_NAME)
    if not token:
        token = secrets.token_hex(24)
        response.set_cookie(
            key=config.WISHLIST_COOKIE_NAME, value=token,
            httponly=True, samesite="lax", secure=config.COOKIE_SECURE, domain=config.COOKIE_DOMAIN, path="/", max_age=60 * 60 * 24 * 365,
        )
    return token


# ----------------------------------------------------------- register / login / logout --

@router.post("/customers/register", response_model=schemas.CustomerOut)
def register_customer(payload: schemas.CustomerRegisterIn, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if db.query(models.Customer).filter(models.Customer.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    customer = models.Customer(
        email=email, password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(), last_name=payload.last_name.strip(),
        phone=payload.phone.strip(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    token = _create_customer_session(db, customer.id)
    response.set_cookie(
        key=config.CUSTOMER_SESSION_COOKIE_NAME, value=token,
        httponly=True, samesite="lax", secure=config.COOKIE_SECURE, domain=config.COOKIE_DOMAIN, path="/", max_age=60 * 60 * 24 * config.CUSTOMER_SESSION_TTL_DAYS,
    )
    return customer


@router.post("/customers/login", response_model=schemas.CustomerOut)
def login_customer(payload: schemas.CustomerLoginIn, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    customer = db.query(models.Customer).filter(models.Customer.email == email).first()
    if not customer or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = _create_customer_session(db, customer.id)
    response.set_cookie(
        key=config.CUSTOMER_SESSION_COOKIE_NAME, value=token,
        httponly=True, samesite="lax", secure=config.COOKIE_SECURE, domain=config.COOKIE_DOMAIN, path="/", max_age=60 * 60 * 24 * config.CUSTOMER_SESSION_TTL_DAYS,
    )
    return customer


@router.post("/customers/logout")
def logout_customer(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(config.CUSTOMER_SESSION_COOKIE_NAME)
    if token:
        db.query(models.CustomerSession).filter(models.CustomerSession.token == token).delete()
        db.commit()
    response.delete_cookie(config.CUSTOMER_SESSION_COOKIE_NAME, path="/", domain=config.COOKIE_DOMAIN)
    return {"ok": True}


@router.get("/customers/me", response_model=schemas.CustomerOut)
def get_my_profile(customer: models.Customer = Depends(get_current_customer)):
    return customer


# ----------------------------------------------------------- addresses --

@router.get("/customers/me/addresses", response_model=list[schemas.CustomerAddressOut])
def list_my_addresses(customer: models.Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    return db.query(models.CustomerAddress).filter(models.CustomerAddress.customer_id == customer.id).all()


@router.post("/customers/me/addresses", response_model=schemas.CustomerAddressOut)
def add_my_address(payload: schemas.CustomerAddressIn, customer: models.Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    if payload.is_default:
        db.query(models.CustomerAddress).filter(models.CustomerAddress.customer_id == customer.id).update({"is_default": False})
    address = models.CustomerAddress(customer_id=customer.id, **payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.delete("/customers/me/addresses/{address_id}")
def delete_my_address(address_id: int, customer: models.Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    address = db.query(models.CustomerAddress).filter(
        models.CustomerAddress.id == address_id, models.CustomerAddress.customer_id == customer.id
    ).first()
    if address:
        db.delete(address)
        db.commit()
    return {"ok": True}


# ----------------------------------------------------------- order history --

@router.get("/customers/me/orders")
def list_my_orders(customer: models.Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    orders = db.query(models.Order).filter(models.Order.customer_id == customer.id).order_by(models.Order.created_at.desc()).all()
    return [
        {
            "order_number": o.order_number, "status": o.status,
            "warranty_status": o.warranty_status or "active", "total": o.total,
            "created_at": o.created_at, "item_count": sum(i.quantity for i in o.items),
        }
        for o in orders
    ]


# ----------------------------------------------------------- wishlist (guest + signed-in) --

def _wishlist_filter(db, customer, guest_token):
    q = db.query(models.WishlistItem)
    if customer:
        return q.filter(models.WishlistItem.customer_id == customer.id)
    return q.filter(models.WishlistItem.guest_token == guest_token)


@router.get("/wishlist", response_model=list[schemas.WishlistItemOut])
def get_wishlist(request: Request, response: Response, db: Session = Depends(get_db), customer: models.Customer | None = Depends(get_optional_customer)):
    guest_token = None if customer else _get_or_create_wishlist_guest_token(request, response)
    items = _wishlist_filter(db, customer, guest_token).all()
    out = []
    for item in items:
        p = item.product
        in_stock = any(v.stock_qty > 0 for v in p.variants) if p.variants else True
        out.append(schemas.WishlistItemOut(
            id=item.id, product_id=p.id, slug=p.slug, title=p.title, price=p.price,
            compare_at_price=p.compare_at_price,
            image=p.images[0].url if p.images else None,
            in_stock=in_stock, added_at=item.added_at,
        ))
    return out


@router.post("/wishlist/{product_id}")
def add_to_wishlist(product_id: int, request: Request, response: Response, db: Session = Depends(get_db), customer: models.Customer | None = Depends(get_optional_customer)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    guest_token = None if customer else _get_or_create_wishlist_guest_token(request, response)
    existing = _wishlist_filter(db, customer, guest_token).filter(models.WishlistItem.product_id == product_id).first()
    if existing:
        return {"ok": True, "already_saved": True}
    db.add(models.WishlistItem(
        customer_id=customer.id if customer else None,
        guest_token=guest_token, product_id=product_id,
    ))
    db.commit()
    return {"ok": True, "already_saved": False}


@router.delete("/wishlist/{product_id}")
def remove_from_wishlist(product_id: int, request: Request, db: Session = Depends(get_db), customer: models.Customer | None = Depends(get_optional_customer)):
    guest_token = request.cookies.get(config.WISHLIST_COOKIE_NAME) if not customer else None
    if not customer and not guest_token:
        return {"ok": True}  # nothing to remove — this visitor has no wishlist yet
    _wishlist_filter(db, customer, guest_token).filter(models.WishlistItem.product_id == product_id).delete()
    db.commit()
    return {"ok": True}
