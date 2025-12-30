"""
SQL Query Converter: Spark SQL → PostgreSQL

Handles syntax differences between Spark SQL and PostgreSQL for Lakebase migration.
"""

import re
import logging

logger = logging.getLogger(__name__)


class SparkToPostgresConverter:
    """Convert Spark SQL queries to PostgreSQL-compatible syntax."""
    
    @staticmethod
    def convert(query: str) -> str:
        """
        Convert Spark SQL query to PostgreSQL syntax.
        
        Key conversions:
        1. LATERAL VIEW explode() → CROSS JOIN LATERAL unnest()
        2. PERCENTILE_CONT() WITHIN GROUP → percentile_cont() WITHIN GROUP
        3. NOW() → CURRENT_TIMESTAMP
        4. INTERVAL syntax
        5. Array functions
        6. Table name references with synced suffix
        """
        converted = query
        
        # 1. Convert LATERAL VIEW explode to PostgreSQL unnest
        converted = SparkToPostgresConverter._convert_lateral_view(converted)
        
        # 2. Convert PERCENTILE_CONT syntax (mostly compatible, but check)
        # PostgreSQL uses same syntax, but ensure proper casting
        
        # 3. Convert NOW() to CURRENT_TIMESTAMP (both work in PostgreSQL, but explicit is better)
        # Keep NOW() as it works in PostgreSQL
        
        # 4. Convert INTERVAL syntax (Spark: "1 HOUR", PostgreSQL: INTERVAL '1 hour')
        converted = SparkToPostgresConverter._convert_intervals(converted)
        
        # 5. Convert date_trunc (syntax is compatible)
        
        # 6. Convert array_contains to PostgreSQL syntax
        converted = SparkToPostgresConverter._convert_array_contains(converted)
        
        # 7. Add table name suffix conversion (_silver → _synced)
        converted = SparkToPostgresConverter._convert_table_names(converted)
        
        # 8. Remove catalog prefix for PostgreSQL (catalog.schema.table → schema.table)
        converted = SparkToPostgresConverter._remove_catalog_prefix(converted)
        
        logger.debug(f"Converted query:\n{converted}")
        return converted
    
    @staticmethod
    def _convert_lateral_view(query: str) -> str:
        """
        Convert Spark's LATERAL VIEW explode to PostgreSQL's CROSS JOIN LATERAL jsonb_array_elements.
        
        Spark: FROM table t LATERAL VIEW explode(column) AS alias
        PostgreSQL: FROM table t CROSS JOIN LATERAL jsonb_array_elements(column) AS alias_value
        
        For JSONB columns in Lakebase, use jsonb_array_elements instead of unnest.
        The alias refers to the entire JSONB object, not a record type.
        """
        # Pattern: LATERAL VIEW explode(column) AS alias
        # Store the alias name to use for field references
        pattern = r'LATERAL\s+VIEW\s+explode\(([^)]+)\)\s+AS\s+(\w+)'
        
        def replace_lateral(match):
            column = match.group(1)
            alias = match.group(2)
            # Store alias for later field conversion
            return f'CROSS JOIN LATERAL jsonb_array_elements({column}) AS {alias}_value'
        
        converted = re.sub(pattern, replace_lateral, query, flags=re.IGNORECASE)
        
        # Now convert field references from alias.field to (alias_value->>'field')
        # Use CAST to ensure correct types for numeric fields
        def convert_field_reference(text, alias):
            # Match alias.field_name patterns
            field_pattern = rf'\b{alias}\.(\w+)\b'
            
            def replace_field(match):
                field_name = match.group(1)
                # Check if this looks like a numeric field (duration, count, etc)
                if any(x in field_name.lower() for x in ['duration', 'count', 'ms', 'error']):
                    # For numeric/boolean fields, cast appropriately
                    if 'error' in field_name.lower():
                        return f"({alias}_value->>'{field_name}')::boolean"
                    else:
                        return f"({alias}_value->>'{field_name}')::float"
                else:
                    # For string fields, just extract as text
                    return f"{alias}_value->>'{field_name}'"
            
            return re.sub(field_pattern, replace_field, text, flags=re.IGNORECASE)
        
        # Find all aliases used
        alias_matches = re.finditer(r'AS\s+(\w+)_value\b', converted, re.IGNORECASE)
        for match in alias_matches:
            original_alias = match.group(1)
            converted = convert_field_reference(converted, original_alias)
        
        return converted
    
    @staticmethod
    def _convert_intervals(query: str) -> str:
        """
        Convert Spark INTERVAL syntax to PostgreSQL.
        
        Spark: INTERVAL 1 HOUR, INTERVAL {interval}
        PostgreSQL: INTERVAL '1 hour', INTERVAL '{interval}'
        """
        # Pattern 1: INTERVAL <number> <unit>
        pattern1 = r'INTERVAL\s+(\d+)\s+(HOUR|MINUTE|DAY|SECOND)'
        replacement1 = r"INTERVAL '\1 \2'"
        converted = re.sub(pattern1, replacement1, query, flags=re.IGNORECASE)
        
        # Pattern 2: INTERVAL {variable} (from f-strings)
        # This requires checking if already quoted
        pattern2 = r'INTERVAL\s+\{([^}]+)\}(?!\s*\')'
        replacement2 = r"INTERVAL '{\1}'"
        converted = re.sub(pattern2, replacement2, converted, flags=re.IGNORECASE)
        
        return converted
    
    @staticmethod
    def _convert_array_contains(query: str) -> str:
        """
        Convert Spark's array_contains to PostgreSQL's ANY operator.
        
        Spark: array_contains(array_column, 'value')
        PostgreSQL: 'value' = ANY(array_column)
        """
        # Pattern: array_contains(column, value)
        pattern = r'array_contains\(([^,]+),\s*([^)]+)\)'
        replacement = r'\2 = ANY(\1)'
        
        converted = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        return converted
    
    @staticmethod
    def _convert_table_names(query: str) -> str:
        """
        Convert table names from Unity Catalog to Lakebase synced tables.
        
        traces_assembled_silver → traces_assembled_synced
        traces_silver → traces_silver_synced
        metrics_1min → metrics_1min_synced
        logs → logs_synced
        """
        # Table name mappings
        replacements = {
            'traces_assembled_silver': 'traces_assembled_synced',
            'traces_silver': 'traces_silver_synced',
            'service_dependencies': 'service_dependencies_synced',  # Assuming this is synced too
        }
        
        converted = query
        for old_name, new_name in replacements.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + old_name + r'\b'
            converted = re.sub(pattern, new_name, converted, flags=re.IGNORECASE)
        
        return converted
    
    @staticmethod
    def _remove_catalog_prefix(query: str) -> str:
        """
        Remove catalog prefix from table references for PostgreSQL.
        
        Spark/Unity Catalog: catalog.schema.table
        PostgreSQL/Lakebase: schema.table
        
        PostgreSQL doesn't support cross-database references.
        """
        # Pattern: catalog.schema.table → schema.table
        # Match: word.word.word where words are identifiers
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
        replacement = r'\2.\3'
        
        converted = re.sub(pattern, replacement, query)
        return converted


def convert_spark_to_postgres(query: str) -> str:
    """Convenience function to convert Spark SQL to PostgreSQL."""
    return SparkToPostgresConverter.convert(query)
