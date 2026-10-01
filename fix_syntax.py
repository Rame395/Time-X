import re

with open("backend/app/routers/products.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'relevance_col = case\(\[\s*\(models\.Product\.title\.ilike\(prefix_like\), 1\),\s*\(models\.Brand\.name\.ilike\(prefix_like\), 2\),\s*\(models\.Product\.title\.ilike\(like\), 3\),\s*else_=4\s*\)'

replacement = """relevance_col = case(
            [
                (models.Product.title.ilike(prefix_like), 1),
                (models.Brand.name.ilike(prefix_like), 2),
                (models.Product.title.ilike(like), 3)
            ],
            else_=4
        )"""

new_content = re.sub(pattern, replacement, content)

with open("backend/app/routers/products.py", "w", encoding="utf-8") as f:
    f.write(new_content)
