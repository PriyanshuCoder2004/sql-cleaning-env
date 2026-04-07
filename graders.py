import sqlite3, re
from models import GraderResult

# ==============================
# 1. NULL FILLING (ADVANCED)
# ==============================
def grade_null_filling(conn):
    rows = conn.execute("SELECT email FROM users").fetchall()
    total = len(rows)

    dirty_patterns = ['null','n/a','none','']

    # ✅ only check current state (NOT original)
    still_dirty = sum(
        1 for (email,) in rows
        if email is None or str(email).strip().lower() in dirty_patterns
    )

    # ✅ perfect solution
    if still_dirty == 0:
        score = 1.0
        verdict = "PASS"
    else:
        score = round(1 - (still_dirty / total), 3)
        verdict = "PARTIAL" if score > 0 else "FAIL"

    return GraderResult(
        score=score,
        breakdown={
            "total": total,
            "still_dirty": still_dirty
        },
        verdict=verdict,
        task_name="null_filling",
        details=f"{still_dirty} dirty values remaining"
    )


# ==============================
# 2. DEDUPLICATION (STRICT)
# ==============================
def grade_deduplication(conn):
    rows = conn.execute("SELECT id, product, amount, customer FROM orders").fetchall()

    total = len(rows)
    unique = len(set(rows))
    duplicates_remaining = total - unique

    if total == 0:
        return GraderResult(0.0, {}, "FAIL", "deduplication", "Empty table")

    # ✅ Reward based on duplicates removed
    score = round(unique / total, 3)

    # 🔥 penalty if too many rows deleted (over-cleaning)
    if unique < total * 0.5:
        score *= 0.7

    verdict = "PASS" if score >= 0.9 else "PARTIAL" if score > 0.5 else "FAIL"

    return GraderResult(
        score=score,
        breakdown={
            "total": total,
            "unique": unique,
            "duplicates_remaining": duplicates_remaining
        },
        verdict=verdict,
        task_name="deduplication",
        details=f"{duplicates_remaining} duplicates remaining"
    )


# ==============================
# 3. SCHEMA NORMALIZATION (HARD 🔥)
# ==============================
def grade_schema_normalization(conn):
    rows = conn.execute("SELECT country, phone FROM contacts").fetchall()
    total = len(rows)

    if total == 0:
        return GraderResult(0.0, {}, "FAIL", "schema_normalization", "Empty table")

    country_ok = 0
    phone_ok = 0

    for country, phone in rows:

        # ✅ Country normalization (multiple formats)
        if str(country).strip().lower() in [
            "united states", "usa", "us", "u.s.a", "u.s"
        ]:
            country_ok += 1

        # ✅ Phone normalization (strict format)
        if phone and re.match(r"^\d{3}-\d{3}-\d{4}$", str(phone).strip()):
            phone_ok += 1

    country_score = country_ok / total
    phone_score = phone_ok / total

    # 🔥 weighted scoring (realistic)
    score = round((0.4 * country_score + 0.6 * phone_score), 3)

    verdict = "PASS" if score >= 0.85 else "PARTIAL" if score >= 0.4 else "FAIL"

    return GraderResult(
        score=score,
        breakdown={
            "country_correct": country_ok,
            "phone_correct": phone_ok,
            "total": total
        },
        verdict=verdict,
        task_name="schema_normalization",
        details=f"Country {country_ok}/{total}, Phone {phone_ok}/{total}"
    )


# ==============================
# 4. TYPE COERCION (REALISTIC)
# ==============================
def grade_type_coercion(conn):
    rows = conn.execute("SELECT price, quantity FROM products").fetchall()
    total = len(rows)

    if total == 0:
        return GraderResult(0.0, {}, "FAIL", "type_coercion", "Empty table")

    price_ok = 0
    qty_ok = 0

    for price, qty in rows:

        # ✅ Price must be clean float
        try:
            p = str(price).strip()
            if not re.search(r"[^\d.]", p):  # no symbols
                float(p)
                price_ok += 1
        except:
            pass

        # ✅ Quantity must be valid integer
        try:
            q = int(str(qty).strip())
            if q > 0:
                qty_ok += 1
        except:
            pass

    price_score = price_ok / total
    qty_score = qty_ok / total

    # 🔥 weighted
    score = round((0.6 * price_score + 0.4 * qty_score), 3)

    verdict = "PASS" if score >= 0.9 else "PARTIAL" if score >= 0.5 else "FAIL"

    return GraderResult(
        score=score,
        breakdown={
            "price_correct": price_ok,
            "qty_correct": qty_ok,
            "total": total
        },
        verdict=verdict,
        task_name="type_coercion",
        details=f"Price {price_ok}/{total}, Qty {qty_ok}/{total}"
    )


# ==============================
# REGISTER
# ==============================
GRADERS = {
    "null_filling": grade_null_filling,
    "deduplication": grade_deduplication,
    "schema_normalization": grade_schema_normalization,
    "type_coercion": grade_type_coercion,
}
