import pytest

from app.services.sql_executor import execute_readonly_sql


@pytest.mark.asyncio
async def test_select_query_executes():

    result = await execute_readonly_sql(
        """
        SELECT
            COUNT(*) AS customer_count
        FROM customers
        """
    )

    assert result["success"] is True
    assert result["row_count"] == 1
    assert result["rows"][0]["customer_count"] == 20


@pytest.mark.asyncio
async def test_existing_limit_is_preserved():

    result = await execute_readonly_sql(
        """
        SELECT *
        FROM products
        LIMIT 5
        """
    )

    assert result["success"] is True
    assert result["row_count"] == 5
    assert "LIMIT 5" in result["executed_sql"].upper()


@pytest.mark.asyncio
async def test_limit_added_when_missing():

    result = await execute_readonly_sql(
        """
        SELECT *
        FROM products
        """
    )

    assert result["success"] is True
    assert result["row_count"] <= 100
    assert "LIMIT 100" in result["executed_sql"].upper()


@pytest.mark.asyncio
async def test_insert_is_rejected():

    result = await execute_readonly_sql(
        """
        INSERT INTO customers
        VALUES (999)
        """
    )

    assert result["success"] is False
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert "SELECT" in result["error"]


@pytest.mark.asyncio
async def test_update_is_rejected():

    result = await execute_readonly_sql(
        """
        UPDATE customers
        SET first_name = 'Test'
        WHERE customer_id = 1
        """
    )

    assert result["success"] is False
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert "SELECT" in result["error"]


@pytest.mark.asyncio
async def test_delete_is_rejected():

    result = await execute_readonly_sql(
        """
        DELETE FROM customers
        WHERE customer_id = 1
        """
    )

    assert result["success"] is False
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert "SELECT" in result["error"]


@pytest.mark.asyncio
async def test_multiple_statements_are_rejected():

    result = await execute_readonly_sql(
        """
        SELECT * FROM customers;
        SELECT * FROM orders;
        """
    )

    assert result["success"] is False
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert "one SQL statement" in result["error"]


@pytest.mark.asyncio
async def test_invalid_sql_is_rejected():

    result = await execute_readonly_sql(
        """
        SELECT FROM
        """
    )

    assert result["success"] is False
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert "Invalid SQL syntax" in result["error"]


@pytest.mark.asyncio
async def test_empty_sql_is_rejected():

    result = await execute_readonly_sql("")

    assert result["success"] is False
    assert result["row_count"] == 0
    assert result["rows"] == []
    assert "empty" in result["error"].lower()


@pytest.mark.asyncio
async def test_join_query_executes():

    result = await execute_readonly_sql(
        """
        SELECT
            p.product_name,
            c.category_name
        FROM products p
        JOIN categories c
            ON p.category_id = c.category_id
        ORDER BY p.product_id
        """
    )

    assert result["success"] is True
    assert result["row_count"] == 20

    first_row = result["rows"][0]

    assert "product_name" in first_row
    assert "category_name" in first_row


@pytest.mark.asyncio
async def test_aggregate_query_executes():

    result = await execute_readonly_sql(
        """
        SELECT
            SUM(total_amount) AS revenue
        FROM orders
        """
    )

    assert result["success"] is True
    assert result["row_count"] == 1
    assert "revenue" in result["rows"][0]
    assert result["rows"][0]["revenue"] is not None


@pytest.mark.asyncio
async def test_2025_revenue_query_executes():

    result = await execute_readonly_sql(
        """
        SELECT
            SUM(total_amount) AS revenue
        FROM orders
        WHERE order_date >= '2025-01-01'
          AND order_date < '2026-01-01'
        """
    )

    assert result["success"] is True
    assert result["row_count"] == 1
    assert result["rows"][0]["revenue"] is not None


@pytest.mark.asyncio
async def test_product_revenue_query_executes():

    result = await execute_readonly_sql(
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

    assert result["success"] is True
    assert result["row_count"] == 5

    first_row = result["rows"][0]

    assert "product_name" in first_row
    assert "revenue" in first_row