from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from sqlalchemy import create_engine, event, text, Engine
from typing import List, Dict, Any, Optional
import os
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class LakebaseManager:
    """Manages connections to Databricks Lakebase (PostgreSQL) with OAuth token refresh."""
    
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
        
        # Lakebase configuration
        # Priority: PGHOST (resource binding) > LAKEBASE_HOST (env var) > SDK lookup (instance name)
        self.instance_name = os.getenv("LAKEBASE_INSTANCE_NAME", "zerobus-dev")
        self.database_name = os.getenv("PGDATABASE", os.getenv("LAKEBASE_DATABASE_NAME", "zerobus_sdp"))
        self.catalog_name = os.getenv("LAKEBASE_CATALOG_NAME", "zerobus_sdp")
        self.schema_name = os.getenv("LAKEBASE_SCHEMA_NAME", "zerobus_sdp")
        self.db_port = int(os.getenv("PGPORT", os.getenv("LAKEBASE_PORT", "5432")))
        self.ssl_mode = os.getenv("LAKEBASE_SSL_MODE", "require")

        # Resolve host: try env vars first, then auto-discover from instance name
        self.db_host = os.getenv("PGHOST") or os.getenv("LAKEBASE_HOST")
        if self.db_host:
            logger.info(f"Using Lakebase host from env: {self.db_host}")
        else:
            # Auto-discover host from Lakebase instance via SDK
            try:
                instance = self.client.database.get_database_instance(name=self.instance_name)
                self.db_host = instance.read_write_dns
                logger.info(f"Auto-discovered Lakebase host from instance '{self.instance_name}': {self.db_host}")
            except Exception as e:
                raise ValueError(
                    f"Lakebase instance '{self.instance_name}' not found. "
                    f"Run full_pipeline_setup to create it, or set LAKEBASE_HOST. Error: {e}"
                )

        # Get connection user: prefer PGUSER from resource binding, fall back to SP client ID
        self.pg_user = os.getenv("PGUSER") or client_id or os.getenv("DATABRICKS_CLIENT_ID")
        
        # OAuth token management
        self.postgres_password: Optional[str] = None
        self.last_password_refresh: float = 0
        self.token_refresh_interval: int = 900  # 15 minutes
        
        # Initialize connection pool
        self._engine: Optional[Engine] = None
    
    def _refresh_token(self) -> str:
        """Generate a fresh OAuth token for Lakebase connection."""
        logger.info(f"Refreshing PostgreSQL OAuth token for instance: {self.instance_name}")
        cred = self.client.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[self.instance_name]
        )
        return cred.token
    
    def _get_engine(self) -> Engine:
        """Get or create SQLAlchemy engine with OAuth token refresh."""
        if self._engine is not None:
            return self._engine
        
        # Build connection string (password will be injected via event listener)
        connection_string = (
            f"postgresql+psycopg2://{self.pg_user}:@{self.db_host}:{self.db_port}/"
            f"{self.database_name}?sslmode={self.ssl_mode}"
        )
        
        # Create engine with connection pooling
        self._engine = create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        
        # Register event listener for OAuth token injection
        @event.listens_for(self._engine, "do_connect")
        def provide_token(dialect, conn_rec, cargs, cparams):
            # Refresh token if expired or not yet set
            if (
                self.postgres_password is None 
                or time.time() - self.last_password_refresh > self.token_refresh_interval
            ):
                self.postgres_password = self._refresh_token()
                self.last_password_refresh = time.time()
            
            cparams["password"] = self.postgres_password
        
        logger.info(f"SQLAlchemy engine created for Lakebase instance: {self.instance_name}")
        return self._engine
    
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against Lakebase and return results as list of dicts.

        Args:
            query: SQL query with %s placeholders for parameters
            params: Optional list of parameters to bind to the query
        """
        query_start = time.time()

        try:
            logger.info("=" * 80)
            logger.info("Executing Lakebase Query")
            logger.info(f"Instance: {self.instance_name}")
            logger.info(f"Database: {self.database_name}")
            logger.info(f"Schema: {self.catalog_name}.{self.schema_name}")
            logger.info("-" * 80)
            logger.debug(f"Query:\n{query}")
            if params:
                logger.debug(f"Parameters: {params}")
            logger.info("-" * 80)

            engine = self._get_engine()

            with engine.connect() as conn:
                # Convert %s placeholders to :param1, :param2, etc. for SQLAlchemy
                if params:
                    # Replace %s with :1, :2, :3, etc.
                    query_with_placeholders = query
                    param_dict = {}
                    for i, param in enumerate(params, 1):
                        # Find and replace the first %s with :param{i}
                        query_with_placeholders = query_with_placeholders.replace('%s', f':param{i}', 1)
                        param_dict[f'param{i}'] = param

                    result = conn.execute(text(query_with_placeholders), param_dict)
                else:
                    result = conn.execute(text(query))

                # Convert result to list of dictionaries
                columns = result.keys()
                results = []
                for row in result:
                    row_dict = dict(zip(columns, row))
                    results.append(row_dict)

                query_duration = time.time() - query_start

                logger.info(f"✅ Query succeeded")
                logger.info(f"   Rows returned: {len(results)}")
                logger.info(f"   Columns: {list(columns)}")
                logger.info(f"   Execution time: {query_duration:.3f}s")
                logger.info("=" * 80)

                return results
        
        except Exception as e:
            query_duration = time.time() - query_start
            logger.error("=" * 80)
            logger.error("❌ Lakebase Query Failed")
            logger.error(f"   Instance: {self.instance_name}")
            logger.error(f"   Database: {self.database_name}")
            logger.error(f"   Error: {e}")
            logger.error(f"   Execution time: {query_duration:.3f}s")
            logger.error("-" * 80)
            logger.error(f"Failed Query:\n{query}")
            logger.error("=" * 80)
            logger.error("Full traceback:", exc_info=True)
            raise
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get Lakebase connection information for debugging."""
        return {
            "instance_name": self.instance_name,
            "database_name": self.database_name,
            "catalog_name": self.catalog_name,
            "schema_name": self.schema_name,
            "host": self.db_host,
            "port": self.db_port,
            "ssl_mode": self.ssl_mode,
            "table_prefix": f"{self.catalog_name}.{self.schema_name}"
        }
