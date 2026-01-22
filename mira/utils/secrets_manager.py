"""Secrets management utilities for Mira platform.

Provides robust secret fetching with retry logic for production environments,
supporting Vault, Kubernetes secrets, and environment variables.
"""
import os
import time
import logging
import base64
from typing import Optional, Dict, Any, Callable
from functools import wraps


logger = logging.getLogger("mira.secrets_manager")


class SecretsManagerError(Exception):
    """Base exception for secrets manager errors."""
    pass


class SecretNotFoundError(SecretsManagerError):
    """Exception raised when a secret is not found."""
    pass


class SecretsManager:
    """
    Secrets manager with retry logic for production environments.
    
    Supports multiple backends:
    - Environment variables (default)
    - HashiCorp Vault (via hvac library)
    - Kubernetes secrets (via kubernetes library)
    """
    
    def __init__(self, backend: str = "env", config: Optional[Dict[str, Any]] = None):
        """
        Initialize secrets manager.
        
        Args:
            backend: Secret backend type ("env", "vault", "k8s")
            config: Backend-specific configuration
        """
        self.backend = backend
        self.config = config or {}
        self.vault_client = None
        self.k8s_client = None
        
        if backend == "vault":
            self._initialize_vault()
        elif backend == "k8s":
            self._initialize_k8s()
            
    def _initialize_vault(self):
        """Initialize Vault client if available."""
        try:
            import hvac
            vault_url = self.config.get("url", os.getenv("VAULT_ADDR"))
            vault_token = self.config.get("token", os.getenv("VAULT_TOKEN"))
            
            if vault_url and vault_token:
                self.vault_client = hvac.Client(url=vault_url, token=vault_token)
                logger.info("Vault client initialized")
            else:
                logger.warning("Vault configuration missing, falling back to env")
                self.backend = "env"
        except ImportError:
            logger.warning("hvac library not available, install with: pip install hvac")
            self.backend = "env"
        except Exception as e:
            logger.error(f"Error initializing Vault: {e}")
            self.backend = "env"
            
    def _initialize_k8s(self):
        """Initialize Kubernetes client if available."""
        try:
            from kubernetes import client, config
            
            # Try loading in-cluster config first, then local kubeconfig
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()
                
            self.k8s_client = client.CoreV1Api()
            logger.info("Kubernetes client initialized")
        except ImportError:
            logger.warning("kubernetes library not available, install with: pip install kubernetes")
            self.backend = "env"
        except Exception as e:
            logger.error(f"Error initializing Kubernetes: {e}")
            self.backend = "env"
            
    def _fetch_with_retry(
        self,
        fetch_func: Callable[[], Any],
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0
    ) -> Any:
        """
        Fetch a secret with retry logic for transient failures.
        
        Args:
            fetch_func: Function to fetch the secret
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries in seconds
            backoff: Backoff multiplier for exponential backoff
            
        Returns:
            Secret value
            
        Raises:
            SecretsManagerError: If all retry attempts fail
        """
        last_error = None
        current_delay = delay
        
        for attempt in range(max_retries + 1):
            try:
                result = fetch_func()
                if attempt > 0:
                    logger.info(f"Secret fetch succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"Secret fetch failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    logger.error(f"Secret fetch failed after {max_retries + 1} attempts")
                    
        raise SecretsManagerError(f"Failed to fetch secret after {max_retries + 1} attempts: {last_error}")
        
    def _fetch_from_env(self, key: str) -> Optional[str]:
        """Fetch secret from environment variables."""
        value = os.getenv(key)
        if value is None:
            raise SecretNotFoundError(f"Secret '{key}' not found in environment")
        return value
        
    def _fetch_from_vault(self, path: str, key: Optional[str] = None) -> Optional[str]:
        """Fetch secret from Vault."""
        if not self.vault_client:
            raise SecretsManagerError("Vault client not initialized")
            
        try:
            secret_response = self.vault_client.secrets.kv.v2.read_secret_version(path=path)
            secret_data = secret_response['data']['data']
            
            if key:
                if key not in secret_data:
                    raise SecretNotFoundError(f"Key '{key}' not found in Vault secret at '{path}'")
                return secret_data[key]
            else:
                return secret_data
        except Exception as e:
            raise SecretsManagerError(f"Error fetching from Vault: {e}")
            
    def _fetch_from_k8s(self, name: str, namespace: str = "default", key: Optional[str] = None) -> Optional[str]:
        """Fetch secret from Kubernetes."""
        if not self.k8s_client:
            raise SecretsManagerError("Kubernetes client not initialized")
            
        try:
            secret = self.k8s_client.read_namespaced_secret(name=name, namespace=namespace)
            secret_data = secret.data
            
            if key:
                if key not in secret_data:
                    raise SecretNotFoundError(f"Key '{key}' not found in K8s secret '{name}'")
                try:
                    return base64.b64decode(secret_data[key]).decode('utf-8')
                except Exception as e:
                    raise SecretsManagerError(f"Error decoding secret '{name}/{key}': {e}")
            else:
                # Return all decoded secrets
                try:
                    return {k: base64.b64decode(v).decode('utf-8') for k, v in secret_data.items()}
                except Exception as e:
                    raise SecretsManagerError(f"Error decoding secrets from '{name}': {e}")
        except Exception as e:
            raise SecretsManagerError(f"Error fetching from Kubernetes: {e}")
            
    def get_secret(
        self,
        identifier: str,
        key: Optional[str] = None,
        default: Optional[str] = None,
        max_retries: int = 3,
        delay: float = 1.0
    ) -> Optional[str]:
        """
        Get a secret from the configured backend with retry logic.
        
        Args:
            identifier: Secret identifier (env var name, Vault path, or K8s secret name)
            key: Optional key within the secret (for Vault/K8s)
            default: Default value if secret not found
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries in seconds
            
        Returns:
            Secret value or default
            
        Raises:
            SecretsManagerError: If fetch fails after retries (when no default provided)
        """
        try:
            if self.backend == "env":
                fetch_func = lambda: self._fetch_from_env(identifier)
            elif self.backend == "vault":
                fetch_func = lambda: self._fetch_from_vault(identifier, key)
            elif self.backend == "k8s":
                namespace = self.config.get("namespace", "default")
                fetch_func = lambda: self._fetch_from_k8s(identifier, namespace, key)
            else:
                raise SecretsManagerError(f"Unknown backend: {self.backend}")
                
            return self._fetch_with_retry(fetch_func, max_retries=max_retries, delay=delay)
            
        except SecretNotFoundError as e:
            if default is not None:
                logger.info(f"Secret not found, using default value: {e}")
                return default
            raise
        except SecretsManagerError:
            if default is not None:
                logger.info(f"Error fetching secret, using default value")
                return default
            raise


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def initialize_secrets_manager(backend: str = "env", config: Optional[Dict[str, Any]] = None):
    """
    Initialize the global secrets manager.
    
    Args:
        backend: Secret backend type ("env", "vault", "k8s")
        config: Backend-specific configuration
    """
    global _secrets_manager
    _secrets_manager = SecretsManager(backend=backend, config=config)
    logger.info(f"Secrets manager initialized with backend: {backend}")


def get_secret(
    identifier: str,
    key: Optional[str] = None,
    default: Optional[str] = None,
    max_retries: int = 3,
    delay: float = 1.0
) -> Optional[str]:
    """
    Get a secret using the global secrets manager.
    
    If no secrets manager is initialized, falls back to environment variables.
    
    Args:
        identifier: Secret identifier
        key: Optional key within the secret
        default: Default value if secret not found
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        
    Returns:
        Secret value or default
    """
    global _secrets_manager
    
    if _secrets_manager is None:
        _secrets_manager = SecretsManager(backend="env")
        
    return _secrets_manager.get_secret(
        identifier=identifier,
        key=key,
        default=default,
        max_retries=max_retries,
        delay=delay
    )
