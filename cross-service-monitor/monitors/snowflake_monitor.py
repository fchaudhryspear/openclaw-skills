"""
Snowflake Monitor
Monitors queries, warehouses, storage, security
"""

import asyncio
import snowflake.connector
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query execution metrics"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_execution_time_ms: float = 0.0
    p99_execution_time_ms: float = 0.0
    credits_used: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        return self.successful_queries / max(self.total_queries, 1)
    
    @property
    def failure_rate(self) -> float:
        return self.failed_queries / max(self.total_queries, 1)


@dataclass
class WarehouseMetrics:
    """Warehouse performance metrics"""
    warehouse_name: str
    state: str = 'UNKNOWN'  # RUNNING, SUSPENDED, RESUMING
    queued_queries: int = 0
    queued_provisioning_queries: int = 0
    active_sessions: int = 0
    cpu_percentage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StorageMetrics:
    """Storage usage metrics"""
    total_bytes: int = 0
    failover_bytes: int = 0
    bytes_per_table: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024 ** 3)


@dataclass
class SecurityMetrics:
    """Security-related metrics"""
    failed_logins_24h: int = 0
    users_with_mfa: int = 0
    total_users: int = 0
    stale_access_keys: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SnowflakeMonitor:
    """Monitor Snowflake for pipeline health"""
    
    def __init__(self, account: str, user: str, 
                 private_key: Optional[str] = None,
                 password: Optional[str] = None,
                 warehouse: str = 'COMPUTE_WH',
                 database: str = 'APPLICATIONS',
                 schema: str = 'PUBLIC',
                 role: str = 'ACCOUNTADMIN'):
        
        self.account = account
        self.user = user
        self.private_key = private_key
        self.password = password
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        self.role = role
        
    def _get_connection(self):
        """Create Snowflake connection"""
        conn_params = {
            'account': self.account,
            'user': self.user,
            'warehouse': self.warehouse,
            'database': self.database,
            'schema': self.schema,
            'role': self.role,
        }
        
        if self.private_key:
            conn_params['private_key'] = self.private_key
        elif self.password:
            conn_params['password'] = self.password
        else:
            raise ValueError("Need either private_key or password for authentication")
            
        return snowflake.connector.connect(**conn_params)
    
    async def check_query_health(self, hours: int = 24) -> QueryMetrics:
        """Check query success/failure rates"""
        metrics = QueryMetrics()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get query statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN EXECUTION_STATUS = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    AVG(TOTAL_ELAPSED_TIME_MS) as avg_time,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY TOTAL_ELAPSED_TIME_MS) as p99_time,
                    SUM(WAREHOUSE_CREDITS_USED) as credits
                FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
                  AND QUERY_TYPE != 'BACKGROUND'
            """)
            
            row = cursor.fetchone()
            if row:
                metrics.total_queries = row[0] or 0
                metrics.successful_queries = row[1] or 0
                metrics.failed_queries = row[2] or 0
                metrics.avg_execution_time_ms = row[3] or 0
                metrics.p99_execution_time_ms = row[4] or 0
                metrics.credits_used = float(row[5]) if row[5] else 0
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking query health: {e}")
            metrics.timestamp = datetime.utcnow()
            
        return metrics
    
    async def get_recent_failed_queries(self, limit: int = 20,
                                       hours: int = 24) -> List[Dict]:
        """Get details of recent failed queries"""
        failures = []
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT 
                    QUERY_ID,
                    QUERY_TEXT,
                    ERROR_MESSAGE,
                    ERROR_NUMBER,
                    START_TIME,
                    TOTAL_ELAPSED_TIME_MS,
                    WAREHOUSE_NAME,
                    DATABASE_NAME,
                    SCHEMA_NAME
                FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
                  AND EXECUTION_STATUS = 'FAILED'
                ORDER BY START_TIME DESC
                LIMIT {limit}
            """)
            
            for row in cursor:
                failures.append({
                    'query_id': row[0],
                    'query_text': row[1][:500] if row[1] else '',  # Truncate
                    'error_message': row[2],
                    'error_number': row[3],
                    'timestamp': row[4].isoformat() if row[4] else None,
                    'execution_time_ms': row[5],
                    'warehouse': row[6],
                    'database': row[7],
                    'schema': row[8]
                })
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error fetching failed queries: {e}")
            
        return failures
    
    async def check_warehouse_status(self, 
                                    warehouse_names: Optional[List[str]] = None) -> Dict[str, WarehouseMetrics]:
        """Check status of all or specific warehouses"""
        results = {}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get warehouse states
            cursor.execute("""
                SELECT 
                    WAREHOUSE_NAME,
                    WAREHOUSE_STATE,
                    QUEUED_PROVISIONING_QUERY_COUNT,
                    QUEUED_LOAD_QUERY_COUNT
                FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_LOAD_HISTORY(
                    DATE_TRUNC('MINUTE', CURRENT_TIMESTAMP())))
                QUALIFY ROW_NUMBER() OVER (PARTITION BY WAREHOUSE_NAME ORDER BY START_TIME DESC) = 1
            """)
            
            warehouse_data = {row[0]: row for row in cursor.fetchall()}
            
            # If specific warehouses requested, filter
            if warehouse_names:
                warehouse_to_check = warehouse_names
            else:
                warehouse_to_check = list(warehouse_data.keys())
                
            # Get session info
            cursor.execute("SELECT WAREHOUSE_NAME, COUNT(*) FROM SESSIONS GROUP BY WAREHOUSE_NAME")
            session_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get CPU usage from WAREHOUSE_METERING_HISTORY
            cursor.execute("""
                SELECT 
                    WAREHOUSE_NAME,
                    AVG(CPU_QUOTA_USED_PERCENTAGE) as avg_cpu
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE USAGE_DATE = CURRENT_DATE()
                GROUP BY WAREHOUSE_NAME
            """)
            cpu_data = {row[0]: row[1] for row in cursor.fetchall()}
            
            for wh_name in warehouse_to_check:
                wd = warehouse_data.get(wh_name, (wh_name, 'UNKNOWN', 0, 0))
                
                metrics = WarehouseMetrics(
                    warehouse_name=wh_name,
                    state=wd[1] if len(wd) > 1 else 'UNKNOWN',
                    queued_queries=wd[3] if len(wd) > 3 else 0,
                    queued_provisioning_queries=wd[2] if len(wd) > 2 else 0,
                    active_sessions=session_counts.get(wh_name, 0),
                    cpu_percentage=cpu_data.get(wh_name, 0.0) or 0.0
                )
                results[wh_name] = metrics
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking warehouse status: {e}")
            
        return results
    
    async def check_storage_usage(self) -> StorageMetrics:
        """Check storage metrics"""
        metrics = StorageMetrics()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Total storage
            cursor.execute("""
                SELECT 
                    SUM(STORAGE_BYTES) + SUM(FAILOVER_BYTES) as total_bytes
                FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
                WHERE USAGE_DATE = CURRENT_DATE()
            """)
            
            row = cursor.fetchone()
            if row:
                metrics.total_bytes = row[0] or 0
                metrics.failover_bytes = row[1] or 0 if len(row) > 1 else 0
            
            # Breakdown by table (top 20)
            cursor.execute("""
                SELECT 
                    TABLE_SCHEMA || '.' || TABLE_NAME as table_name,
                    STORAGE_BYTES
                FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
                WHERE DELETED_ON IS NULL
                ORDER BY STORAGE_BYTES DESC
                LIMIT 20
            """)
            
            for row in cursor:
                metrics.bytes_per_table[row[0]] = row[1] or 0
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking storage: {e}")
            
        return metrics
    
    async def check_security_metrics(self) -> SecurityMetrics:
        """Check security-related metrics"""
        metrics = SecurityMetrics()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Failed logins in last 24h
            cursor.execute("""
                SELECT COUNT(*)
                FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
                WHERE EVENT_TIMESTAMP >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
                  AND IS_SUCCESS = 'NO'
            """)
            metrics.failed_logins_24h = cursor.fetchone()[0] or 0
            
            # Users with MFA
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN EXT_AUTHENTICATION_DUO = TRUE OR SECOND_FACTOR_ENABLED = TRUE THEN 1 END) as mfa_users
                FROM SNOWFLAKE.ACCOUNT_USAGE.USERS
                WHERE DELETED_ON IS NULL
            """)
            row = cursor.fetchone()
            metrics.total_users = row[0] or 0
            metrics.users_with_mfa = row[1] or 0 if len(row) > 1 else 0
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking security metrics: {e}")
            
        return metrics
    
    async def get_pipeline_data_freshness(self, 
                                         table_name: str,
                                         time_column: str,
                                         schema: str = 'PUBLIC') -> Dict:
        """Check how fresh data is in a specific table"""
        result = {
            'table': f"{schema}.{table_name}",
            'status': 'unknown',
            'last_update': None,
            'age_minutes': None,
            'row_count': 0
        }
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get last update time
            cursor.execute(f"""
                SELECT MAX({time_column}) as last_update, COUNT(*) as row_count
                FROM {schema}.{table_name}
            """)
            
            row = cursor.fetchone()
            if row and row[0]:
                last_update = row[0]
                result['last_update'] = last_update.isoformat()
                result['row_count'] = row[1] or 0
                
                age = datetime.utcnow().replace(tzinfo=last_update.tzinfo) - last_update
                result['age_minutes'] = age.total_seconds() / 60
                
                if result['age_minutes'] < 60:
                    result['status'] = 'healthy'
                elif result['age_minutes'] < 240:
                    result['status'] = 'warning'
                else:
                    result['status'] = 'critical'
                    
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking data freshness for {table_name}: {e}")
            result['error'] = str(e)
            
        return result
    
    async def check_table_dependencies(self, tables: List[Dict]) -> Dict:
        """
        Check multiple tables for pipeline dependencies
        Each table dict: {'schema': str, 'name': str, 'time_column': str, 'max_age_minutes': int}
        """
        results = {
            'status': 'healthy',
            'tables': {},
            'issues': [],
            'checked_at': datetime.utcnow().isoformat()
        }
        
        for table_config in tables:
            freshness = await self.get_pipeline_data_freshness(
                table_name=table_config['name'],
                time_column=table_config['time_column'],
                schema=table_config.get('schema', 'PUBLIC')
            )
            
            table_key = f"{freshness['table']}"
            results['tables'][table_key] = freshness
            
            # Check against threshold
            max_age = table_config.get('max_age_minutes', 60)
            if freshness['age_minutes'] is not None:
                if freshness['age_minutes'] > max_age * 2:
                    results['status'] = 'critical'
                    results['issues'].append({
                        'type': 'data_stale',
                        'resource': table_key,
                        'severity': 'critical',
                        'message': f"Data is {freshness['age_minutes']:.0f} min old (max: {max_age} min)"
                    })
                elif freshness['age_minutes'] > max_age:
                    results['status'] = 'warning'
                    results['issues'].append({
                        'type': 'data_lagging',
                        'resource': table_key,
                        'severity': 'warning',
                        'message': f"Data is {freshness['age_minutes']:.0f} min old (threshold: {max_age} min)"
                    })
                    
        return results
    
    async def get_warehouse_credit_usage(self, days: int = 7) -> Dict:
        """Get credit usage trends"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT 
                    USAGE_DATE,
                    WAREHOUSE_NAME,
                    CREDITS_USED,
                    CREDITS_USED_BY_AUTOSUSPEND
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE USAGE_DATE >= DATEADD(day, -{days}, CURRENT_DATE())
                ORDER BY USAGE_DATE DESC, WAREHOUSE_NAME
            """)
            
            usage = []
            for row in cursor:
                usage.append({
                    'date': row[0].isoformat() if row[0] else None,
                    'warehouse': row[1],
                    'credits_used': float(row[2]) if row[2] else 0,
                    'autosuspend_credits': float(row[3]) if row[3] else 0
                })
                
            cursor.close()
            conn.close()
            
            return {
                'period_days': days,
                'usage': usage,
                'total_credits': sum(u['credits_used'] for u in usage)
            }
            
        except Exception as e:
            logger.error(f"Error getting credit usage: {e}")
            return {'error': str(e)}
