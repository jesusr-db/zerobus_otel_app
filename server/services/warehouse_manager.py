from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from databricks.sdk.core import Config
from typing import List, Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)


class WarehouseManager:
    def __init__(self, user_token: Optional[str] = None):
        try:
            client_id = os.getenv("DATABRICKS_CLIENT_ID")
            client_secret = os.getenv("DATABRICKS_CLIENT_SECRET")
            host = os.getenv("DATABRICKS_HOST")
            
            if client_id and client_secret and host:
                config = Config(
                    host=host,
                    client_id=client_id,
                    client_secret=client_secret
                )
                self.client = WorkspaceClient(config=config)
                logger.info("WorkspaceClient initialized with app service principal")
            else:
                self.client = WorkspaceClient()
                logger.info("WorkspaceClient initialized with default config")
        except Exception as e:
            logger.error(f"Failed to initialize WorkspaceClient: {e}")
            raise
        self._warehouse_id: Optional[str] = None
        self.user_token = user_token

    def _auto_detect_warehouse(self) -> str:
        warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if warehouse_id:
            logger.info(f"Using warehouse from DATABRICKS_WAREHOUSE_ID: {warehouse_id}")
            return warehouse_id
        
        warehouses = list(self.client.warehouses.list())
        
        if not warehouses:
            raise ValueError("No SQL warehouses found in the workspace")
        
        running_warehouses = [w for w in warehouses if w.state.value == "RUNNING"]
        
        if running_warehouses:
            return running_warehouses[0].id
        
        return warehouses[0].id

    def get_warehouse_id(self) -> str:
        if self._warehouse_id is None:
            self._warehouse_id = self._auto_detect_warehouse()
        return self._warehouse_id

    def get_warehouse_info(self) -> Dict[str, Any]:
        warehouse_id = self.get_warehouse_id()
        warehouse = self.client.warehouses.get(warehouse_id)
        return {
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "status": warehouse.state.value if warehouse.state else "UNKNOWN",
        }

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        try:
            warehouse_id = self.get_warehouse_id()
            logger.info(f"Executing query on warehouse: {warehouse_id}")
            
            if self.user_token:
                host = os.getenv("DATABRICKS_HOST")
                user_config = Config(
                    host=host,
                    token=self.user_token,
                    client_id=None,
                    client_secret=None
                )
                user_client = WorkspaceClient(config=user_config)
                logger.info("Using user token for SQL query execution")
                
                statement = user_client.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=query,
                    wait_timeout="30s"
                )
            else:
                statement = self.client.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=query,
                    wait_timeout="30s"
                )
            
            if statement.status.state != StatementState.SUCCEEDED:
                error_message = statement.status.error.message if statement.status.error else "Unknown error"
                logger.error(f"Query failed: {error_message}")
                raise RuntimeError(f"Query failed: {error_message}")
            
            if not statement.result or not statement.result.data_array:
                logger.info("Query returned no results")
                return []
            
            columns = [col.name for col in statement.manifest.schema.columns]
            
            results = []
            for row in statement.result.data_array:
                row_dict = dict(zip(columns, row))
                results.append(row_dict)
            
            logger.info(f"Query returned {len(results)} rows")
            return results
        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            raise
