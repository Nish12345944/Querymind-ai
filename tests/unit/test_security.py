import pytest

from app.services.sql_validator import validate_sql
from app.services.sql_executor import execute_readonly_sql


# ============================================================
# STACKED / MULTI-STATEMENT INJECTION
# ============================================================

@pytest.mark.asyncio
async def test_reject_stacked_statements():
    result = await validate_sql(
        "SELECT * FROM customers; DROP TABLE customers"
    )
    assert result["valid"] is False
    assert result["checks"]["single_statement"] is False


@pytest.mark.asyncio
async def test_reject_stacked_insert():
    result = await validate_sql(
        "SELECT * FROM customers; INSERT INTO customers VALUES (999, 'x', 'x', 'x@x.com', 'x', 1, '2024-01-01', 'x')"
    )
    assert result["valid"] is False
    assert result["checks"]["single_statement"] is False


# ============================================================
# WRITE OPERATIONS BLOCKED BY VALIDATOR
# ============================================================

@pytest.mark.asyncio
async def test_validator_blocks_insert():
    result = await validate_sql(
        "INSERT INTO customers (first_name) VALUES ('hacked')"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_update():
    result = await validate_sql(
        "UPDATE customers SET first_name = 'hacked' WHERE 1=1"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_delete():
    result = await validate_sql(
        "DELETE FROM customers WHERE 1=1"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_drop():
    result = await validate_sql(
        "DROP TABLE customers"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_truncate():
    result = await validate_sql(
        "TRUNCATE TABLE customers"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_alter():
    result = await validate_sql(
        "ALTER TABLE customers ADD COLUMN pwned TEXT"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_create():
    result = await validate_sql(
        "CREATE TABLE evil (id INT)"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_grant():
    result = await validate_sql(
        "GRANT ALL PRIVILEGES ON customers TO public"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_revoke():
    result = await validate_sql(
        "REVOKE ALL ON customers FROM public"
    )
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validator_blocks_select_into():
    result = await validate_sql(
        "SELECT customer_id INTO customer_backup FROM customers"
    )
    assert result["valid"] is False
    assert "SELECT INTO" in result["reason"]


@pytest.mark.asyncio
async def test_validator_blocks_row_locking():
    result = await validate_sql(
        "SELECT customer_id FROM customers FOR UPDATE"
    )
    assert result["valid"] is False
    assert "locking" in result["reason"].lower()


# ============================================================
# WRITE OPERATIONS BLOCKED BY EXECUTOR
# ============================================================

@pytest.mark.asyncio
async def test_executor_blocks_insert():
    result = await execute_readonly_sql(
        "INSERT INTO customers (first_name) VALUES ('hacked')"
    )
    assert result["success"] is False
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_executor_blocks_update():
    result = await execute_readonly_sql(
        "UPDATE customers SET first_name = 'hacked' WHERE 1=1"
    )
    assert result["success"] is False
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_executor_blocks_delete():
    result = await execute_readonly_sql(
        "DELETE FROM customers WHERE 1=1"
    )
    assert result["success"] is False
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_executor_blocks_drop():
    result = await execute_readonly_sql(
        "DROP TABLE customers"
    )
    assert result["success"] is False
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_executor_blocks_truncate():
    result = await execute_readonly_sql(
        "TRUNCATE TABLE customers"
    )
    assert result["success"] is False
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_executor_blocks_select_into():
    result = await execute_readonly_sql(
        "SELECT customer_id INTO customer_backup FROM customers"
    )
    assert result["success"] is False
    assert result["rows"] == []


@pytest.mark.asyncio
async def test_executor_blocks_for_update():
    result = await execute_readonly_sql(
        "SELECT customer_id FROM customers FOR UPDATE"
    )
    assert result["success"] is False
    assert result["rows"] == []


# ============================================================
# LIMIT SAFETY
# ============================================================

@pytest.mark.asyncio
async def test_executor_caps_oversized_limit():
    result = await execute_readonly_sql(
        "SELECT * FROM customers LIMIT 9999"
    )
    assert result["success"] is True
    assert result["row_count"] <= 100


@pytest.mark.asyncio
async def test_executor_rejects_zero_limit():
    result = await execute_readonly_sql(
        "SELECT * FROM customers LIMIT 0"
    )
    assert result["success"] is False
    assert "greater than zero" in result["error"].lower()
