import pytest

from app.services.sql_validator import validate_sql


# ============================================================
# VALID SQL
# ============================================================

@pytest.mark.asyncio
async def test_valid_select():
    result = await validate_sql(
        "SELECT COUNT(*) AS customer_count FROM customers"
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_valid_join():
    result = await validate_sql(
        """
        SELECT
            c.first_name,
            c.last_name
        FROM customers c
        JOIN orders o
            ON c.customer_id = o.customer_id
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_valid_aggregate_alias():
    result = await validate_sql(
        """
        SELECT
            SUM(oi.quantity * oi.unit_price) AS revenue
        FROM order_items oi
        ORDER BY revenue DESC
        """
    )

    assert result["valid"] is True


# ============================================================
# EMPTY / INVALID SQL
# ============================================================

@pytest.mark.asyncio
async def test_empty_sql():
    result = await validate_sql("")

    assert result["valid"] is False


@pytest.mark.asyncio
async def test_invalid_sql_syntax():
    result = await validate_sql(
        "SELECT FROM"
    )

    assert result["valid"] is False


# ============================================================
# UNSUPPORTED
# ============================================================

@pytest.mark.asyncio
async def test_unsupported():
    result = await validate_sql("UNSUPPORTED")

    assert result["valid"] is False
    assert result["checks"]["unsupported"] is True


# ============================================================
# MULTIPLE STATEMENTS
# ============================================================

@pytest.mark.asyncio
async def test_multiple_statements():
    result = await validate_sql(
        """
        SELECT * FROM customers;
        SELECT * FROM orders;
        """
    )

    assert result["valid"] is False
    assert result["checks"]["single_statement"] is False


# ============================================================
# WRITE OPERATIONS
# ============================================================

@pytest.mark.asyncio
async def test_reject_insert():
    result = await validate_sql(
        "INSERT INTO customers (first_name) VALUES ('Test')"
    )

    assert result["valid"] is False


@pytest.mark.asyncio
async def test_reject_update():
    result = await validate_sql(
        "UPDATE customers SET first_name = 'Test'"
    )

    assert result["valid"] is False


@pytest.mark.asyncio
async def test_reject_delete():
    result = await validate_sql(
        "DELETE FROM customers"
    )

    assert result["valid"] is False


@pytest.mark.asyncio
async def test_reject_drop():
    result = await validate_sql(
        "DROP TABLE customers"
    )

    assert result["valid"] is False


@pytest.mark.asyncio
async def test_reject_alter():
    result = await validate_sql(
        "ALTER TABLE customers ADD COLUMN test_column TEXT"
    )

    assert result["valid"] is False


@pytest.mark.asyncio
async def test_reject_truncate():
    result = await validate_sql(
        "TRUNCATE TABLE customers"
    )

    assert result["valid"] is False


# ============================================================
# UNKNOWN TABLES
# ============================================================

@pytest.mark.asyncio
async def test_unknown_table():
    result = await validate_sql(
        "SELECT * FROM employee_reviews"
    )

    assert result["valid"] is False
    assert result["checks"]["tables"] is False


# ============================================================
# UNKNOWN COLUMNS
# ============================================================

@pytest.mark.asyncio
async def test_unknown_column():
    result = await validate_sql(
        "SELECT employee_happiness_score FROM customers"
    )

    assert result["valid"] is False
    assert result["checks"]["columns"] is False


# ============================================================
# INVALID JOIN RELATIONSHIP
# ============================================================

@pytest.mark.asyncio
async def test_invalid_join_relationship():
    result = await validate_sql(
        """
        SELECT
            c.first_name,
            p.product_name
        FROM customers c
        JOIN products p
            ON c.customer_id = p.product_id
        """
    )

    assert result["valid"] is False
    assert result["checks"]["join_relationships"] is False


# ============================================================
# VALID REAL-WORLD QUERIES FROM EVALUATION
# ============================================================

@pytest.mark.asyncio
async def test_customer_count_query():
    result = await validate_sql(
        """
        SELECT COUNT(*) AS customer_count
        FROM customers
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_order_count_query():
    result = await validate_sql(
        """
        SELECT COUNT(*) AS order_count
        FROM orders
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_2025_order_count_query():
    result = await validate_sql(
        """
        SELECT COUNT(*) AS order_count
        FROM orders
        WHERE order_date >= '2025-01-01'
          AND order_date < '2026-01-01'
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_2025_revenue_query():
    result = await validate_sql(
        """
        SELECT
            SUM(total_amount) AS revenue
        FROM orders
        WHERE order_date >= '2025-01-01'
          AND order_date < '2026-01-01'
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_product_category_query():
    result = await validate_sql(
        """
        SELECT
            p.product_name,
            c.category_name
        FROM products p
        JOIN categories c
            ON p.category_id = c.category_id
        ORDER BY c.category_name, p.product_name
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_store_region_query():
    result = await validate_sql(
        """
        SELECT
            s.store_name,
            r.region_name
        FROM stores s
        JOIN regions r
            ON s.region_id = r.region_id
        ORDER BY r.region_name, s.store_name
        """
    )

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_product_revenue_query():
    result = await validate_sql(
        """
        SELECT
            p.product_name,
            SUM(
                oi.quantity
                * oi.unit_price
                * (1 - COALESCE(oi.discount, 0))
            ) AS revenue
        FROM order_items oi
        JOIN products p
            ON oi.product_id = p.product_id
        JOIN orders o
            ON oi.order_id = o.order_id
        GROUP BY
            p.product_id,
            p.product_name
        ORDER BY revenue DESC
        LIMIT 5
        """
    )

    assert result["valid"] is True