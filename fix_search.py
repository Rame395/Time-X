import re

with open("backend/app/routers/products.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'    if search:\s*q = q\.outerjoin\(models\.Brand\)\s*like = f"%\{search\.strip\(\)\}%"\s*q = q\.filter\(\s*\(models\.Product\.title\.ilike\(like\)\)\s*\| \(models\.Product\.subcategory\.ilike\(like\)\)\s*\| \(models\.Product\.department\.ilike\(like\)\)\s*\| \(models\.Product\.description\.ilike\(like\)\)\s*\| \(models\.Brand\.name\.ilike\(like\)\)\s*\)\s*if sort == "price_asc":\s*q = q\.order_by\(models\.Product\.price\.asc\(\)\)\s*elif sort == "price_desc":\s*q = q\.order_by\(models\.Product\.price\.desc\(\)\)\s*elif sort == "popularity":\s*q = q\.order_by\(models\.Product\.display_rank\.asc\(\), models\.Product\.is_best_seller\.desc\(\), models\.Product\.created_at\.desc\(\)\)\s*else:\s*q = q\.order_by\(models\.Product\.display_rank\.asc\(\), models\.Product\.created_at\.desc\(\)\)'

replacement = """    relevance_col = None
    if search:
        from sqlalchemy import case
        q = q.outerjoin(models.Brand)
        clean_search = search.strip()
        like = f"%{clean_search}%"
        prefix_like = f"{clean_search}%"
        
        q = q.filter(
            (models.Product.title.ilike(like))
            | (models.Product.subcategory.ilike(like))
            | (models.Product.department.ilike(like))
            | (models.Product.description.ilike(like))
            | (models.Brand.name.ilike(like))
        )
        
        relevance_col = case(
            (models.Product.title.ilike(prefix_like), 1),
            (models.Brand.name.ilike(prefix_like), 2),
            (models.Product.title.ilike(like), 3),
            else_=4
        )

    if sort == "price_asc":
        q = q.order_by(models.Product.price.asc())
    elif sort == "price_desc":
        q = q.order_by(models.Product.price.desc())
    elif sort == "popularity":
        if relevance_col is not None:
            q = q.order_by(relevance_col.asc(), models.Product.display_rank.asc(), models.Product.is_best_seller.desc(), models.Product.created_at.desc())
        else:
            q = q.order_by(models.Product.display_rank.asc(), models.Product.is_best_seller.desc(), models.Product.created_at.desc())
    else:
        if relevance_col is not None:
            q = q.order_by(relevance_col.asc(), models.Product.display_rank.asc(), models.Product.created_at.desc())
        else:
            q = q.order_by(models.Product.display_rank.asc(), models.Product.created_at.desc())"""

new_content = re.sub(pattern, replacement, content)

if new_content != content:
    with open("backend/app/routers/products.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Relevance sorting injected successfully.")
else:
    print("Regex match failed.")
