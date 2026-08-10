from app.services.schema_service import (
    get_database_schema
)


async def get_valid_relationships():

    schema = await get_database_schema()

    relationships = set()

    for table_name, table_info in schema.items():

        for foreign_key in table_info["foreign_keys"]:

            source = (
                table_name,
                foreign_key["column"]
            )

            target = (
                foreign_key["references_table"],
                foreign_key["references_column"]
            )

            relationships.add(
                (source, target)
            )

            relationships.add(
                (target, source)
            )

    return relationships