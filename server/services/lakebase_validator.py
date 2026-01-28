"""
Lakebase Validator

Utilities for validating Lakebase connectivity and queries.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from server.services.lakebase_manager import LakebaseManager

logger = logging.getLogger(__name__)


class LakebaseValidator:
    """Validate Lakebase connectivity with detailed logging."""

    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
        self.lakebase_manager = None

    def test_connectivity(self) -> Dict[str, Any]:
        """
        Test connectivity to Lakebase.
        Returns detailed connection status for debugging.
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "lakebase": {"connected": False, "error": None}
        }

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


def validate_lakebase_setup(user_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to validate Lakebase connectivity.

    Usage:
        from server.services.lakebase_validator import validate_lakebase_setup
        results = validate_lakebase_setup()
    """
    validator = LakebaseValidator(user_token=user_token)

    logger.info("🚀 Starting Lakebase Validation")
    logger.info("=" * 80)

    # Test connectivity
    connectivity_results = validator.test_connectivity()

    results = {
        "validation_timestamp": datetime.utcnow().isoformat(),
        "connectivity": connectivity_results,
        "overall_status": connectivity_results["lakebase"]["connected"]
    }

    if results["overall_status"]:
        logger.info("✅ Validation passed - Lakebase is accessible")
    else:
        logger.error("❌ Validation failed - check Lakebase connectivity")

    return results
