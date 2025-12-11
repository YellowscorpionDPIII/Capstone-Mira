"""Secrets management integration for Mira platform."""
import os
import logging
from typing import Dict, Any, Optional, Callable
import threading
import time
from abc import ABC, abstractmethod


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""
    
    @abstractmethod
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Retrieve a secret from the backend.
        
        Args:
            path: Path to the secret
            key: Optional specific key within the secret
            
        Returns:
            Secret value
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the backend is available.
        
        Returns:
            True if backend is available
        """
        pass


class VaultBackend(SecretsBackend):
    """HashiCorp Vault backend for secrets."""
    
    def __init__(self, vault_url: str, vault_token: str, mount_point: str = 'secret'):
        """
        Initialize Vault backend.
        
        Args:
            vault_url: URL of the Vault server
            vault_token: Authentication token for Vault
            mount_point: Mount point for KV secrets engine
        """
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.mount_point = mount_point
        self.logger = logging.getLogger("mira.secrets.vault")
        self.client = None
        
        try:
            import hvac
            self.client = hvac.Client(url=vault_url, token=vault_token)
        except ImportError:
            self.logger.warning("hvac library not installed. Vault backend not available.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Vault client: {e}")
    
    def is_available(self) -> bool:
        """Check if Vault is available."""
        if not self.client:
            return False
        try:
            return self.client.is_authenticated()
        except Exception:
            return False
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Retrieve a secret from Vault.
        
        Args:
            path: Path to the secret in Vault
            key: Optional specific key within the secret
            
        Returns:
            Secret value or dict of values
        """
        if not self.client:
            raise RuntimeError("Vault client not initialized")
        
        try:
            # Read secret from Vault (KV v2)
            secret_response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point
            )
            
            data = secret_response['data']['data']
            
            if key:
                return data.get(key)
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret from Vault: {e}")
            raise


class KubernetesSecretsBackend(SecretsBackend):
    """Kubernetes Secrets backend."""
    
    def __init__(self, namespace: str = 'default'):
        """
        Initialize Kubernetes Secrets backend.
        
        Args:
            namespace: Kubernetes namespace to read secrets from
        """
        self.namespace = namespace
        self.logger = logging.getLogger("mira.secrets.k8s")
        self.client = None
        
        try:
            from kubernetes import client, config
            config.load_incluster_config()
            self.client = client.CoreV1Api()
        except Exception as e:
            self.logger.warning(f"Kubernetes client not available: {e}")
    
    def is_available(self) -> bool:
        """Check if Kubernetes API is available."""
        return self.client is not None
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Retrieve a secret from Kubernetes.
        
        Args:
            path: Name of the Kubernetes secret
            key: Optional specific key within the secret
            
        Returns:
            Secret value or dict of values
        """
        if not self.client:
            raise RuntimeError("Kubernetes client not initialized")
        
        try:
            import base64
            secret = self.client.read_namespaced_secret(path, self.namespace)
            
            # Decode base64-encoded secret data
            data = {}
            for k, v in secret.data.items():
                data[k] = base64.b64decode(v).decode('utf-8')
            
            if key:
                return data.get(key)
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret from Kubernetes: {e}")
            raise


class EnvironmentBackend(SecretsBackend):
    """Environment variables backend (fallback)."""
    
    def __init__(self):
        """Initialize environment backend."""
        self.logger = logging.getLogger("mira.secrets.env")
    
    def is_available(self) -> bool:
        """Environment backend is always available."""
        return True
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Retrieve a secret from environment variables.
        
        Args:
            path: Environment variable name (or prefix if key is provided)
            key: Optional suffix for the environment variable name
            
        Returns:
            Secret value
        """
        env_var = f"{path}_{key}" if key else path
        return os.getenv(env_var)


class SecretsManager:
    """
    Centralized secrets management with support for multiple backends.
    
    Supports HashiCorp Vault, Kubernetes Secrets, and environment variables.
    """
    
    def __init__(self, backend: Optional[SecretsBackend] = None, 
                 refresh_interval: int = 3600):
        """
        Initialize secrets manager.
        
        Args:
            backend: Secrets backend to use (defaults to environment)
            refresh_interval: Interval in seconds to refresh secrets (default: 3600)
        """
        self.logger = logging.getLogger("mira.secrets")
        self.backend = backend or EnvironmentBackend()
        self.refresh_interval = refresh_interval
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.refresh_callbacks: Dict[str, list] = {}
        self.refresh_thread: Optional[threading.Thread] = None
        self.running = False
        
        if not self.backend.is_available():
            self.logger.warning(f"Backend {type(self.backend).__name__} not available, using fallback")
            self.backend = EnvironmentBackend()
    
    def get_secret(self, path: str, key: Optional[str] = None, 
                   use_cache: bool = True) -> Any:
        """
        Retrieve a secret.
        
        Args:
            path: Path to the secret
            key: Optional specific key within the secret
            use_cache: Whether to use cached value if available
            
        Returns:
            Secret value
        """
        cache_key = f"{path}:{key}" if key else path
        
        # Return cached value if available and not expired
        if use_cache and cache_key in self.cache:
            age = time.time() - self.cache_timestamps.get(cache_key, 0)
            if age < self.refresh_interval:
                return self.cache[cache_key]
        
        # Fetch secret from backend
        try:
            value = self.backend.get_secret(path, key)
            
            # Cache the value
            self.cache[cache_key] = value
            self.cache_timestamps[cache_key] = time.time()
            
            return value
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {path}: {e}")
            # Return cached value as fallback if available
            if cache_key in self.cache:
                self.logger.warning(f"Returning stale cached value for {path}")
                return self.cache[cache_key]
            raise
    
    def register_refresh_callback(self, path: str, callback: Callable[[Any], None]):
        """
        Register a callback to be called when a secret is refreshed.
        
        Args:
            path: Path to the secret
            callback: Callback function that takes the new secret value
        """
        if path not in self.refresh_callbacks:
            self.refresh_callbacks[path] = []
        self.refresh_callbacks[path].append(callback)
    
    def start_auto_refresh(self):
        """Start automatic secret refresh in background thread."""
        if self.running:
            return
        
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
        self.logger.info("Started automatic secret refresh")
    
    def stop_auto_refresh(self):
        """Stop automatic secret refresh."""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        self.logger.info("Stopped automatic secret refresh")
    
    def _refresh_loop(self):
        """Background loop to refresh secrets."""
        while self.running:
            try:
                time.sleep(self.refresh_interval)
                self._refresh_all_secrets()
            except Exception as e:
                self.logger.error(f"Error in refresh loop: {e}")
    
    def _refresh_all_secrets(self):
        """Refresh all cached secrets."""
        for cache_key in list(self.cache.keys()):
            try:
                # Parse cache key (use rsplit to handle paths with colons)
                if ':' in cache_key:
                    parts = cache_key.rsplit(':', 1)
                    path, key = parts[0], parts[1]
                else:
                    path, key = cache_key, None
                
                # Fetch new value
                old_value = self.cache.get(cache_key)
                new_value = self.backend.get_secret(path, key)
                
                # Update cache
                self.cache[cache_key] = new_value
                self.cache_timestamps[cache_key] = time.time()
                
                # Call refresh callbacks if value changed
                if old_value != new_value and path in self.refresh_callbacks:
                    for callback in self.refresh_callbacks[path]:
                        try:
                            callback(new_value)
                        except Exception as e:
                            self.logger.error(f"Error in refresh callback for {path}: {e}")
                
                self.logger.debug(f"Refreshed secret: {path}")
                
            except Exception as e:
                self.logger.error(f"Failed to refresh secret {cache_key}: {e}")


def create_secrets_manager(config: Dict[str, Any]) -> SecretsManager:
    """
    Create a secrets manager based on configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured SecretsManager instance
    """
    backend_type = config.get('secrets.backend', 'env')
    refresh_interval = config.get('secrets.refresh_interval', 3600)
    
    backend = None
    
    if backend_type == 'vault':
        vault_url = config.get('secrets.vault.url')
        vault_token = config.get('secrets.vault.token')
        mount_point = config.get('secrets.vault.mount_point', 'secret')
        
        if vault_url and vault_token:
            backend = VaultBackend(vault_url, vault_token, mount_point)
    
    elif backend_type == 'kubernetes':
        namespace = config.get('secrets.kubernetes.namespace', 'default')
        backend = KubernetesSecretsBackend(namespace)
    
    return SecretsManager(backend, refresh_interval)


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get the global secrets manager instance.
    
    Returns:
        SecretsManager instance
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def set_secrets_manager(manager: SecretsManager):
    """
    Set the global secrets manager instance.
    
    Args:
        manager: SecretsManager instance to set
    """
    global _secrets_manager
    _secrets_manager = manager
