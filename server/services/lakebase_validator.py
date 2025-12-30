"""
Lakebase Migration Validator

Utilities for validating Lakebase connectivity, query conversion, and result comparison.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from server.services.warehouse_manager import WarehouseManager
from server.services.lakebase_manager import LakebaseManager
from server.services.sql_converter import convert_spark_to_postgres

logger = logging.getLogger(__name__)


class LakebaseValidator:
    """Validate Lakebase migration with detailed logging and comparison."""
    
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
        self.warehouse_manager = None
        self.lakebase_manager = None
        
    def test_connectivity(self) -> Dict[str, Any]:
        """
        Test connectivity to both Warehouse and Lakebase.
        Returns detailed connection status for debugging.
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "warehouse": {"connected": False, "error": None},
            "lakebase": {"connected": False, "error": None}
        }
        
        # Test SQL Warehouse connection
        logger.info("=" * 80)
        logger.info("Testing SQL Warehouse Connectivity")
        logger.info("=" * 80)
        try:
            self.warehouse_manager = WarehouseManager(user_token=self.user_token)
            warehouse_info = self.warehouse_manager.get_warehouse_info()
            results["warehouse"] = {
                "connected": True,
                "error": None,
                "info": warehouse_info
            }
            logger.info(f"✅ SQL Warehouse connected: {warehouse_info}")
        except Exception as e:
            results["warehouse"]["error"] = str(e)
            logger.error(f"❌ SQL Warehouse connection failed: {e}", exc_info=True)
        
        # Test Lakebase connection
        logger.info("=" * 80)
        logger.info("Testing Lakebase Connectivity")
        logger.info("=" * 80)
        try:
            self.lakebase_manager = LakebaseManager(user_token=self.user_token)
            lakebase_info = self.lakebase_manager.get_connection_info()
            
            # Test actual connection with simple query
            test_query = "SELECT 1 as test"
            test_result = self.lakebase_manager.execute_query(test_query)
            
            results["lakebase"] = {
                "connected": True,
                "error": None,
                "info": lakebase_info,
                "test_query_result": test_result
            }
            logger.info(f"✅ Lakebase connected: {lakebase_info}")
            logger.info(f"✅ Test query result: {test_result}")
        except Exception as e:
            results["lakebase"]["error"] = str(e)
            logger.error(f"❌ Lakebase connection failed: {e}", exc_info=True)
        
        logger.info("=" * 80)
        logger.info("Connectivity Test Complete")
        logger.info("=" * 80)
        
        return results
    
    def validate_query_conversion(self, spark_query: str, endpoint_name: str = "unknown") -> Dict[str, Any]:
        """
        Validate Spark SQL to PostgreSQL conversion with detailed logging.
        
        Args:
            spark_query: Original Spark SQL query
            endpoint_name: Name of endpoint for logging context
            
        Returns:
            Dictionary with conversion results and validation info
        """
        logger.info("=" * 80)
        logger.info(f"Query Conversion Validation: {endpoint_name}")
        logger.info("=" * 80)
        
        results = {
            "endpoint": endpoint_name,
            "timestamp": datetime.utcnow().isoformat(),
            "spark_query": spark_query,
            "postgres_query": None,
            "conversion_success": False,
            "changes_detected": []
        }
        
        try:
            # Convert query
            postgres_query = convert_spark_to_postgres(spark_query)
            results["postgres_query"] = postgres_query
            results["conversion_success"] = True
            
            # Log original query
            logger.info("📝 Original Spark SQL Query:")
            logger.info("-" * 80)
            for i, line in enumerate(spark_query.split('\n'), 1):
                logger.info(f"{i:3d} | {line}")
            logger.info("-" * 80)
            
            # Log converted query
            logger.info("🔄 Converted PostgreSQL Query:")
            logger.info("-" * 80)
            for i, line in enumerate(postgres_query.split('\n'), 1):
                logger.info(f"{i:3d} | {line}")
            logger.info("-" * 80)
            
            # Detect and log changes
            changes = self._detect_query_changes(spark_query, postgres_query)
            results["changes_detected"] = changes
            
            if changes:
                logger.info("🔍 Detected Query Changes:")
                for change in changes:
                    logger.info(f"  • {change}")
            else:
                logger.warning("⚠️  No changes detected - verify conversion is working!")
            
            logger.info("✅ Query conversion successful")
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"❌ Query conversion failed: {e}", exc_info=True)
        
        logger.info("=" * 80)
        return results
    
    def compare_results(
        self, 
        spark_query: str, 
        endpoint_name: str = "unknown",
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Execute same query on both backends and compare results.
        
        Args:
            spark_query: Original Spark SQL query
            endpoint_name: Name of endpoint for logging context
            limit: Number of sample rows to log (default 5)
            
        Returns:
            Dictionary with comparison results
        """
        logger.info("=" * 80)
        logger.info(f"Result Comparison: {endpoint_name}")
        logger.info("=" * 80)
        
        results = {
            "endpoint": endpoint_name,
            "timestamp": datetime.utcnow().isoformat(),
            "warehouse": {"success": False, "row_count": 0, "error": None},
            "lakebase": {"success": False, "row_count": 0, "error": None},
            "match": False,
            "differences": []
        }
        
        # Initialize managers if needed
        if not self.warehouse_manager:
            self.warehouse_manager = WarehouseManager(user_token=self.user_token)
        if not self.lakebase_manager:
            self.lakebase_manager = LakebaseManager(user_token=self.user_token)
        
        # Execute on SQL Warehouse
        logger.info("📊 Executing on SQL Warehouse...")
        warehouse_results = None
        try:
            warehouse_results = self.warehouse_manager.execute_query(spark_query)
            results["warehouse"] = {
                "success": True,
                "row_count": len(warehouse_results),
                "error": None,
                "sample_rows": warehouse_results[:limit] if warehouse_results else []
            }
            logger.info(f"✅ Warehouse returned {len(warehouse_results)} rows")
            self._log_sample_results("Warehouse", warehouse_results, limit)
        except Exception as e:
            results["warehouse"]["error"] = str(e)
            logger.error(f"❌ Warehouse query failed: {e}", exc_info=True)
        
        # Execute on Lakebase
        logger.info("📊 Executing on Lakebase...")
        lakebase_results = None
        try:
            postgres_query = convert_spark_to_postgres(spark_query)
            lakebase_results = self.lakebase_manager.execute_query(postgres_query)
            results["lakebase"] = {
                "success": True,
                "row_count": len(lakebase_results),
                "error": None,
                "sample_rows": lakebase_results[:limit] if lakebase_results else []
            }
            logger.info(f"✅ Lakebase returned {len(lakebase_results)} rows")
            self._log_sample_results("Lakebase", lakebase_results, limit)
        except Exception as e:
            results["lakebase"]["error"] = str(e)
            logger.error(f"❌ Lakebase query failed: {e}", exc_info=True)
        
        # Compare results
        if warehouse_results is not None and lakebase_results is not None:
            logger.info("🔍 Comparing Results...")
            comparison = self._compare_result_sets(warehouse_results, lakebase_results)
            results["match"] = comparison["match"]
            results["differences"] = comparison["differences"]
            
            if comparison["match"]:
                logger.info("✅ Results match!")
            else:
                logger.warning("⚠️  Results differ:")
                for diff in comparison["differences"]:
                    logger.warning(f"  • {diff}")
        
        logger.info("=" * 80)
        return results
    
    def _detect_query_changes(self, original: str, converted: str) -> List[str]:
        """Detect specific changes made during conversion."""
        changes = []
        
        # Check for specific conversions
        if "LATERAL VIEW" in original.upper() and "CROSS JOIN LATERAL" in converted.upper():
            changes.append("LATERAL VIEW explode → CROSS JOIN LATERAL unnest")
        
        if "INTERVAL " in original.upper() and "INTERVAL '" in converted.upper():
            changes.append("INTERVAL syntax quoted for PostgreSQL")
        
        if "array_contains" in original.lower() and "ANY(" in converted.upper():
            changes.append("array_contains → ANY operator")
        
        if "_silver" in original.lower() and "_synced" in converted.lower():
            changes.append("Table names: _silver → _synced")
        
        return changes
    
    def _log_sample_results(self, backend_name: str, results: List[Dict], limit: int):
        """Log sample results in readable format."""
        if not results:
            logger.info(f"{backend_name} returned no results")
            return
        
        logger.info(f"{backend_name} Sample Results (showing {min(limit, len(results))} of {len(results)}):")
        logger.info("-" * 80)
        
        for i, row in enumerate(results[:limit], 1):
            logger.info(f"Row {i}:")
            for key, value in row.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                logger.info(f"  {key}: {value_str}")
            logger.info("")
    
    def _compare_result_sets(
        self, 
        warehouse_results: List[Dict], 
        lakebase_results: List[Dict]
    ) -> Dict[str, Any]:
        """Compare two result sets and identify differences."""
        differences = []
        
        # Compare row counts
        if len(warehouse_results) != len(lakebase_results):
            differences.append(
                f"Row count mismatch: Warehouse={len(warehouse_results)}, "
                f"Lakebase={len(lakebase_results)}"
            )
        
        # Compare column names (use first row)
        if warehouse_results and lakebase_results:
            warehouse_cols = set(warehouse_results[0].keys())
            lakebase_cols = set(lakebase_results[0].keys())
            
            missing_in_lakebase = warehouse_cols - lakebase_cols
            extra_in_lakebase = lakebase_cols - warehouse_cols
            
            if missing_in_lakebase:
                differences.append(f"Columns missing in Lakebase: {missing_in_lakebase}")
            if extra_in_lakebase:
                differences.append(f"Extra columns in Lakebase: {extra_in_lakebase}")
            
            # Compare first few rows for value differences
            rows_to_compare = min(3, len(warehouse_results), len(lakebase_results))
            for i in range(rows_to_compare):
                row_diffs = self._compare_rows(
                    warehouse_results[i], 
                    lakebase_results[i], 
                    i + 1
                )
                differences.extend(row_diffs)
        
        return {
            "match": len(differences) == 0,
            "differences": differences
        }
    
    def _compare_rows(self, warehouse_row: Dict, lakebase_row: Dict, row_num: int) -> List[str]:
        """Compare individual rows and identify value differences."""
        differences = []
        
        common_cols = set(warehouse_row.keys()) & set(lakebase_row.keys())
        
        for col in common_cols:
            w_val = warehouse_row[col]
            l_val = lakebase_row[col]
            
            # Handle numeric comparisons with tolerance
            if isinstance(w_val, (int, float)) and isinstance(l_val, (int, float)):
                if abs(w_val - l_val) > 0.01:  # 1% tolerance
                    differences.append(
                        f"Row {row_num}, column '{col}': "
                        f"Warehouse={w_val}, Lakebase={l_val}"
                    )
            elif w_val != l_val:
                differences.append(
                    f"Row {row_num}, column '{col}': "
                    f"Warehouse={w_val}, Lakebase={l_val}"
                )
        
        return differences


def validate_lakebase_setup(user_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to run full validation suite.
    
    Usage:
        from server.services.lakebase_validator import validate_lakebase_setup
        results = validate_lakebase_setup()
    """
    validator = LakebaseValidator(user_token=user_token)
    
    logger.info("🚀 Starting Lakebase Migration Validation Suite")
    logger.info("=" * 80)
    
    # Test connectivity
    connectivity_results = validator.test_connectivity()
    
    results = {
        "validation_timestamp": datetime.utcnow().isoformat(),
        "connectivity": connectivity_results,
        "overall_status": (
            connectivity_results["warehouse"]["connected"] and 
            connectivity_results["lakebase"]["connected"]
        )
    }
    
    if results["overall_status"]:
        logger.info("✅ Validation suite passed - both backends are accessible")
    else:
        logger.error("❌ Validation suite failed - check connectivity issues")
    
    return results
