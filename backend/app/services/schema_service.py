from sqlalchemy import text

from app.db.database import AsyncSessionLocal


async def get_database_schema():
    async with AsyncSessionLocal() as session:

        # ---------------------------------------------------------
        # 1. Get tables and columns
        # ---------------------------------------------------------

        columns_query = text("""
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)

        columns_result = await session.execute(columns_query)
        column_rows = columns_result.mappings().all()

        schema = {}

        for row in column_rows:

            table_name = row["table_name"]

            if table_name not in schema:
                schema[table_name] = {
                    "columns": [],
                    "primary_keys": [],
                    "foreign_keys": []
                }

            schema[table_name]["columns"].append({
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES"
            })

        # ---------------------------------------------------------
        # 2. Get primary keys
        # ---------------------------------------------------------

        primary_key_query = text("""
            SELECT
                tc.table_name,
                kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.ordinal_position;
        """)

        primary_key_result = await session.execute(primary_key_query)
        primary_key_rows = primary_key_result.mappings().all()

        for row in primary_key_rows:

            table_name = row["table_name"]

            if table_name in schema:
                schema[table_name]["primary_keys"].append(
                    row["column_name"]
                )

        # ---------------------------------------------------------
        # 3. Get foreign keys
        # ---------------------------------------------------------

        foreign_key_query = text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)

        foreign_key_result = await session.execute(foreign_key_query)
        foreign_key_rows = foreign_key_result.mappings().all()

        for row in foreign_key_rows:

            table_name = row["table_name"]

            if table_name in schema:
                schema[table_name]["foreign_keys"].append({
                    "column": row["column_name"],
                    "references_table": row["referenced_table"],
                    "references_column": row["referenced_column"]
                })

        return schema