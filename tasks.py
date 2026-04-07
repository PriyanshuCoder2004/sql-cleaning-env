import random
from dataclasses import dataclass
from typing import Dict

@dataclass
class Task:
    id: str
    name: str
    difficulty: str
    description: str
    table_name: str
    passing_threshold: float
    max_steps: int = 10

    def get_setup_sql(self) -> str:
        return self._generate_sql()

    def _generate_sql(self) -> str:
        return ""

class NullFillingTask(Task):
    def _generate_sql(self) -> str:
        # Randomness — different dirty patterns each episode
        null_variants = [None, "", "null", "NULL", "N/A", "none"]
        rows = [
            (1, 'Alice', 'alice@example.com', 30),
            (2, 'Bob',   random.choice(null_variants), 25),
            (3, 'Carol', 'carol@example.com', 28),
            (4, 'Dave',  random.choice(null_variants), 35),
            (5, 'Eve',   'eve@example.com', 22),
            (6, 'Frank', random.choice(null_variants), 40),
            (7, 'Grace', 'grace@example.com', 27),
        ]
        inserts = []
        for r in rows:
            email = f"'{r[2]}'" if r[2] not in (None,) else "NULL"
            inserts.append(f"({r[0]}, '{r[1]}', {email}, {r[3]})")

        return f"""
            DROP TABLE IF EXISTS users;
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, age INTEGER);
            INSERT INTO users VALUES {', '.join(inserts)};
        """

class DeduplicationTask(Task):
    def _generate_sql(self) -> str:
        # Randomness — random number of duplicates each episode
        num_dupes = random.choice([2, 3, 4])
        base_rows = [
            (1, 'Widget',       9.99,  'Alice'),
            (2, 'Gadget',      24.99,  'Bob'),
            (3, 'Doohickey',   4.99,  'Carol'),
            (4, 'Thingamajig', 14.99, 'Dave'),
            (5, 'Sprocket',    7.49,  'Eve'),
        ]
        all_rows = list(base_rows)
        # Add random duplicates
        for _ in range(num_dupes):
            all_rows.append(random.choice(base_rows))

        random.shuffle(all_rows)
        inserts = [f"({r[0]}, '{r[1]}', {r[2]}, '{r[3]}')" for r in all_rows]
        return f"""
            DROP TABLE IF EXISTS orders;
            CREATE TABLE orders (id INTEGER, product TEXT, amount REAL, customer TEXT);
            INSERT INTO orders VALUES {', '.join(inserts)};
        """

class SchemaNormalizationTask(Task):
    def _generate_sql(self) -> str:
        # Randomness — different country/phone format variants
        country_variants = ['US', 'usa', 'u.s.a', 'USA', 'united states', 'U.S.', 'United States of America', 'us']
        phone_variants   = ['5551234567', '(555)123-4567', '555.123.4567', '555 123 4567', '1-555-123-4567']

        rows = [
            (1, 'Alice', 'United States',              '555-123-4567'),
            (2, 'Bob',   random.choice(country_variants), random.choice(phone_variants)),
            (3, 'Carol', random.choice(country_variants), random.choice(phone_variants)),
            (4, 'Dave',  random.choice(country_variants), random.choice(phone_variants)),
            (5, 'Eve',   'United States',              '555-123-4567'),
            (6, 'Frank', random.choice(country_variants), random.choice(phone_variants)),
            (7, 'Grace', random.choice(country_variants), random.choice(phone_variants)),
        ]
        inserts = [f"({r[0]}, '{r[1]}', '{r[2]}', '{r[3]}')" for r in rows]
        return f"""
            DROP TABLE IF EXISTS contacts;
            CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT, country TEXT, phone TEXT);
            INSERT INTO contacts VALUES {', '.join(inserts)};
        """

class TypeCoercionTask(Task):
    def _generate_sql(self) -> str:
        # Randomness — different messy formats each episode
        price_variants = [
          lambda p: f"${p}",
          lambda p: f"£{p}",
          lambda p: f"€{p}",
          lambda p: f"{p} USD",
          lambda p: f"{p},00",
          lambda p: f" {p} ",
          lambda p: f"USD {p}",
       ]
        
        qty_variants = [
            lambda q: f"{q} units",
            lambda q: f"{q}pcs",
            lambda q: f"{q}x",
            lambda q: f"{q} pieces",
            lambda q: f"{q}pc",
        ]
        prices = [9.99, 24.50, 15.0, 100.00, 8.99, 49.99]
        qtys   = [3, 12, 5, 1, 20, 7]

        rows = []
        for i, (price, qty) in enumerate(zip(prices, qtys), 1):
            fmt_price = random.choice(price_variants)(price)
            fmt_qty   = random.choice(qty_variants)(qty)
            rows.append(f"({i}, 'Widget {chr(64+i)}', '{fmt_price}', '{fmt_qty}')")

        return f"""
            DROP TABLE IF EXISTS products;
            CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price TEXT, quantity TEXT);
            INSERT INTO products VALUES {', '.join(rows)};
        """

TASKS: Dict[str, Task] = {
    "null_filling": NullFillingTask(
        id="null_filling",
        name="Null value filling",
        difficulty="easy",
        description="Fill missing or invalid email values with 'unknown@example.com'. Some emails may be NULL, empty string, or 'null'/'N/A'.",
        table_name="users",
        passing_threshold=0.8,
    ),
    "deduplication": DeduplicationTask(
        id="deduplication",
        name="Row deduplication",
        difficulty="medium",
        description="Remove all duplicate rows keeping exactly one copy of each unique record.",
        table_name="orders",
        passing_threshold=0.85,
    ),
    "schema_normalization": SchemaNormalizationTask(
        id="schema_normalization",
        name="Schema normalization",
        difficulty="hard",
        description="Normalize country column to 'United States' and phone to XXX-XXX-XXXX format.",
        table_name="contacts",
        passing_threshold=0.85,
    ),
    "type_coercion": TypeCoercionTask(
        id="type_coercion",
        name="Type coercion",
        difficulty="hard",
        description="Convert messy price strings and quantity strings to clean numeric values.",
        table_name="products",
        passing_threshold=0.9,
    ),
}

def get_task(task_name: str) -> Task:
    if task_name not in TASKS:
        raise ValueError(f"Unknown task '{task_name}'. Available: {list(TASKS.keys())}")
    return TASKS[task_name]

def list_tasks():
    return [
        {
            "id": t.id,
            "name": t.name,
            "difficulty": t.difficulty,
            "description": t.description,
            "max_steps": t.max_steps,
            "passing_threshold": t.passing_threshold,
        }
        for t in TASKS.values()
    ]
