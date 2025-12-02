"""Configuration management for Aithon Core SDK."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import configparser
from contextlib import contextmanager
from dotenv import load_dotenv
import logging

from .types import PathConfig

logger = logging.getLogger(__name__)


# Global map for G_* variables (initialized once at app startup)
GLOBAL_VARS: Dict[str, str] = {}


class ConfigManager:
    """Centralized configuration management for all Aithon services."""

    def __init__(self, app_type: str = "msb", config_root: Optional[Path] = None):
        """Load .envvar and expose simple accessors for G_* variables only."""
        self.app_type = app_type
        self.config_root = config_root or self._find_project_root()
        self.env_path = self.config_root / ".envvar"
        self.logger = logging.getLogger(__name__)

        self._config = configparser.ConfigParser()
        self._config.optionxform = str
        if self.env_path.exists():
            self._config.read(self.env_path)
        else:
            self.logger.error(f"config file not found: {self.env_path}")

    def _find_project_root(self) -> Path:
        """Find the project root by searching upwards for .envvar."""
        current = Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            if (parent / ".envvar").exists():
                return parent
        return Path(__file__).parent.parent

    def get_g_vars(self, section: Optional[str] = None) -> Dict[str, str]:
        """Return only variables starting with G_ (exact case), optionally scoped to a section."""
        result: Dict[str, str] = {}
        if section:
            if section in self._config:
                for k, v in self._config[section].items():
                    if k.startswith("G_"):
                        result[k] = v
            return result

        # All sections
        for sec in self._config.sections():
            for k, v in self._config[sec].items():
                if k.startswith("G_"):
                    result[k] = v
        return result

    def get_var(
        self, key: str, section: Optional[str] = None, fallback: Optional[str] = None
    ) -> Optional[str]:
        """Get an exact variable by key (case-sensitive). Optionally restrict to a section."""
        try:
            if section:
                return self._config.get(section, key, fallback=fallback)
            # Search all sections
            for sec in self._config.sections():
                if key in self._config[sec]:
                    return self._config[sec][key]
            return fallback
        except Exception:
            return fallback

    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI API configuration."""
        return {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0")),
            "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
        }

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Check essential file
        if not self.env_path.exists():
            issues.append(f"environment config file missing: {self.env_path}")

        # Check OpenAI config
        openai_config = self.get_openai_config()
        if not openai_config["api_key"]:
            issues.append("OpenAI API key not configured")

        return issues

    def create_database_manager(self):
        """Create a DatabaseManager instance using centralized config."""
        return DatabaseManager(self.get_database_config())

    def get_database_config(self) -> Dict[str, Any]:
        """Return PostgreSQL connection configuration from centralized .envvar.

        Keys are normalized for psycopg2.connect(**params).
        """
        return {
            "host": self.get_var(
                "G_POSTGRES_HOST", section="POSTGRES", fallback="localhost"
            ),
            "database": self.get_var(
                "G_POSTGRES_DATABASE", section="POSTGRES", fallback="postgres"
            ),
            "user": self.get_var(
                "G_POSTGRES_USER", section="POSTGRES", fallback="postgres"
            ),
            "password": self.get_var(
                "G_POSTGRES_PASSWORD", section="POSTGRES", fallback="postgres"
            ),
            "port": self.get_var("G_POSTGRES_PORT", section="POSTGRES", fallback="5432"),
        }


class DatabaseManager:
    """
    Centralized database manager for all Aithon services.

    Replaces all the duplicated DatabaseManager classes throughout the codebase.
    Uses centralized configuration from ConfigManager.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with database configuration."""
        self.connection_params = self._resolve_db_config(config)
        self._connection = None
        self.logger = logging.getLogger(__name__)

    def _resolve_db_config(
        self, override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Resolve DB config from provided dict or centralized .envvar, normalized for psycopg2."""
        source = override or {}

        # Use centralized configuration - SINGLE SOURCE OF TRUTH
        config_manager = ConfigManager(app_type="common")

        host = source.get(
            "host",
            config_manager.get_var(
                "G_POSTGRES_HOST", section="POSTGRES", fallback="localhost"
            ),
        )
        database = source.get(
            "database",
            config_manager.get_var(
                "G_POSTGRES_DATABASE", section="POSTGRES", fallback="postgres"
            ),
        )
        user = source.get(
            "user",
            config_manager.get_var(
                "G_POSTGRES_USER", section="POSTGRES", fallback="postgres"
            ),
        )
        password = source.get(
            "password",
            config_manager.get_var(
                "G_POSTGRES_PASSWORD", section="POSTGRES", fallback="postgres"
            ),
        )
        port_val: Any = source.get(
            "port",
            config_manager.get_var(
                "G_POSTGRES_PORT", section="POSTGRES", fallback="5432"
            ),
        )

        return {
            "host": str(host),
            "database": str(database),
            "user": str(user),
            "password": str(password),
            "port": str(port_val),  # psycopg2 accepts string
        }

    def get_connection(self):
        """Get database connection, create new if needed."""
        try:
            import psycopg2

            if self._connection is None or self._connection.closed:
                self._connection = psycopg2.connect(**self.connection_params)
                self.logger.info("✅ Connected to PostgreSQL database")
            return self._connection
        except ImportError:
            self.logger.error(
                "❌ psycopg2 not installed. Install with: pip install psycopg2-binary"
            )
            raise
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {e}")
            raise

    def close_connection(self):
        """Close database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self.logger.info("📤 Database connection closed")

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as list of dictionaries."""
        try:
            import psycopg2.extras

            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                if cursor.description:  # SELECT query
                    return [dict(row) for row in cursor.fetchall()]
                else:  # INSERT/UPDATE/DELETE
                    conn.commit()
                    return []
        except Exception as e:
            self.logger.error(f"❌ Query execution failed: {e}")
            raise

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor operations."""
        import psycopg2.extras

        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Database transaction failed: {e}")
            raise
        finally:
            cursor.close()

    def __del__(self):
        """Cleanup on destruction."""
        self.close_connection()

    def get_path_config(self) -> PathConfig:
        """Return simple path config using G_ variables from .envvar."""
        try:
            data_folders: List[str] = []
            section = self.app_type.upper()

            # Common data folder (optional)
            G_datafolder = self.get_var("G_datafolder", section="COMMON", fallback="")
            if not G_datafolder:
                self.logger.warning("missing G_datafolder in [COMMON]")

            # App-specific data/output
            data_key = f"G_{section.lower()}_datafolder"
            output_key = f"G_{section.lower()}_outputfolder"

            G_app_datafolder = self.get_var(data_key, section=section, fallback="")
            if not G_app_datafolder and section == "MSB":
                # MSB specific fallback
                G_app_datafolder = self.get_var(
                    "G_msb_e2e_datafolder", section="MSB", fallback=""
                )

            if not G_app_datafolder:
                self.logger.warning(f"missing {data_key} in [{section}]")

            G_app_outputfolder = self.get_var(output_key, section=section, fallback="")
            if not G_app_outputfolder and section == "MSB":
                G_app_outputfolder = self.get_var(
                    "G_msb_outputfolder", section="MSB", fallback=""
                )

            if not G_app_outputfolder:
                self.logger.warning(f"missing {output_key} in [{section}]")

            # Order: app-specific first, then common
            if G_app_datafolder:
                data_folders.append(G_app_datafolder)
            if G_datafolder:
                data_folders.append(G_datafolder)

            return PathConfig(
                data_folders=data_folders, output_folder=G_app_outputfolder
            )
        except Exception as e:
            self.logger.error(f"error loading path config: {str(e)}")
            return PathConfig(data_folders=[], output_folder="")


def init_global_vars(app_type: str = "msb") -> Dict[str, str]:
    """Load G_* variables from .envvar into GLOBAL_VARS and os.environ.

    - Reads [COMMON] and the app-specific section (e.g., [MSB])
    - Keeps variable names EXACTLY as in .envvar (e.g., G_datafolder)
    - Makes them available via `GLOBAL_VARS` and `os.environ`
    """
    cfg = ConfigManager(app_type=app_type)

    combined: Dict[str, str] = {}
    # COMMON first
    for k, v in cfg.get_g_vars("COMMON").items():
        combined[k] = v

    # App-specific section
    section = app_type.upper()
    for k, v in cfg.get_g_vars(section).items():
        combined[k] = v

    # Update process env and module globals
    for key, val in combined.items():
        os.environ[key] = val

    GLOBAL_VARS.clear()
    GLOBAL_VARS.update(combined)
    return GLOBAL_VARS


def get_global(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a G_* variable by exact key from initialized globals (or env as fallback)."""
    if key in GLOBAL_VARS:
        return GLOBAL_VARS[key]
    return os.getenv(key, default)
