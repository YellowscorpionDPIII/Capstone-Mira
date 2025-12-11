"""Secrets management integration for Vault and Kubernetes Secrets."""
import os
import logging
from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
import threading
import time


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""
    
    @abstractmethod
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Get a secret from the backend.
        
        Args:
            path: Path to the secret
            key: Optional key within the secret (for KV stores)
            
        Returns:
            Secret value
        """
        pass
        
    @abstractmethod
    def list_secrets(self, path: str) -> list:
        """
        List secrets at a path.
        
        Args:
            path: Path to list secrets from
            
        Returns:
            List of secret names
        """
        pass


class VaultBackend(SecretsBackend):
    """Vault secrets backend."""
    
    def __init__(self, vault_addr: str, token: Optional[str] = None, 
                 namespace: Optional[str] = None, mount_point: str = 'secret'):
        """
        Initialize Vault backend.
        
        Args:
            vault_addr: Vault server address
            token: Vault token (can also be set via VAULT_TOKEN env var)
            namespace: Vault namespace (optional)
            mount_point: Secret mount point (default: 'secret')
        """
        self.logger = logging.getLogger("mira.secrets.vault")
        
        try:
            import hvac
            self.hvac = hvac
        except ImportError:
            raise ImportError("hvac library is required for Vault backend. Install with: pip install hvac")
            
        self.vault_addr = vault_addr
        self.token = token or os.getenv('VAULT_TOKEN')
        self.namespace = namespace
        self.mount_point = mount_point
        
        if not self.token:
            raise ValueError("Vault token is required (set VAULT_TOKEN env var or pass token parameter)")
            
        self.client = hvac.Client(
            url=vault_addr,
            token=self.token,
            namespace=namespace
        )
        
        if not self.client.is_authenticated():
            raise ValueError("Failed to authenticate with Vault")
            
        self.logger.info(f"Initialized Vault backend at {vault_addr}")
        
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Get a secret from Vault.
        
        Args:
            path: Path to the secret
            key: Optional key within the secret
            
        Returns:
            Secret value
        """
        try:
            # Read secret from Vault KV v2
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point
            )
            
            data = response['data']['data']
            
            if key:
                return data.get(key)
            return data
        except Exception as e:
            self.logger.error(f"Error reading secret from Vault: {e}")
            raise
            
    def list_secrets(self, path: str) -> list:
        """
        List secrets at a Vault path.
        
        Args:
            path: Path to list secrets from
            
        Returns:
            List of secret names
        """
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point
            )
            return response['data']['keys']
        except Exception as e:
            self.logger.error(f"Error listing secrets from Vault: {e}")
            raise


class KubernetesBackend(SecretsBackend):
    """Kubernetes Secrets backend."""
    
    def __init__(self, namespace: str = 'default', in_cluster: bool = True):
        """
        Initialize Kubernetes Secrets backend.
        
        Args:
            namespace: Kubernetes namespace
            in_cluster: Whether running in-cluster (uses ServiceAccount token)
        """
        self.logger = logging.getLogger("mira.secrets.kubernetes")
        
        try:
            from kubernetes import client, config
            self.k8s_client = client
            self.k8s_config = config
        except ImportError:
            raise ImportError("kubernetes library is required for Kubernetes backend. Install with: pip install kubernetes")
            
        self.namespace = namespace
        
        # Load kubernetes config
        try:
            if in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()
        except Exception as e:
            self.logger.error(f"Error loading Kubernetes config: {e}")
            raise
            
        self.v1 = client.CoreV1Api()
        self.logger.info(f"Initialized Kubernetes Secrets backend for namespace '{namespace}'")
        
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Get a secret from Kubernetes.
        
        Args:
            path: Secret name
            key: Optional key within the secret data
            
        Returns:
            Secret value (base64 decoded)
        """
        try:
            secret = self.v1.read_namespaced_secret(path, self.namespace)
            
            if not secret.data:
                return None
                
            if key:
                import base64
                encoded_value = secret.data.get(key)
                if encoded_value:
                    return base64.b64decode(encoded_value).decode('utf-8')
                return None
            
            # Return all keys decoded
            import base64
            return {
                k: base64.b64decode(v).decode('utf-8')
                for k, v in secret.data.items()
            }
        except Exception as e:
            self.logger.error(f"Error reading secret from Kubernetes: {e}")
            raise
            
    def list_secrets(self, path: str = '') -> list:
        """
        List secrets in Kubernetes namespace.
        
        Args:
            path: Unused for Kubernetes (kept for interface compatibility)
            
        Returns:
            List of secret names
        """
        try:
            secrets = self.v1.list_namespaced_secret(self.namespace)
            return [secret.metadata.name for secret in secrets.items]
        except Exception as e:
            self.logger.error(f"Error listing secrets from Kubernetes: {e}")
            raise


class SecretsManager:
    """
    Secrets manager with support for multiple backends.
    
    Provides a unified interface for accessing secrets from different
    backends (Vault, Kubernetes) with auto-refresh support.
    """
    
    def __init__(self, backend: SecretsBackend):
        """
        Initialize secrets manager.
        
        Args:
            backend: Secrets backend to use
        """
        self.backend = backend
        self.logger = logging.getLogger("mira.secrets")
        self.cache: Dict[str, Any] = {}
        self.refresh_callbacks: Dict[str, list] = {}
        self._refresh_thread: Optional[threading.Thread] = None
        self._refresh_running = False
        self._refresh_interval = 300  # 5 minutes default
        
    def get_secret(self, path: str, key: Optional[str] = None, 
                   use_cache: bool = True) -> Any:
        """
        Get a secret.
        
        Args:
            path: Path to the secret
            key: Optional key within the secret
            use_cache: Whether to use cached value
            
        Returns:
            Secret value
        """
        cache_key = f"{path}:{key}" if key else path
        
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
            
        value = self.backend.get_secret(path, key)
        self.cache[cache_key] = value
        
        return value
        
    def list_secrets(self, path: str = '') -> list:
        """
        List available secrets.
        
        Args:
            path: Path to list secrets from
            
        Returns:
            List of secret names
        """
        return self.backend.list_secrets(path)
        
    def register_refresh_callback(self, path: str, callback: Callable[[Any], None],
                                  key: Optional[str] = None):
        """
        Register a callback to be called when a secret is refreshed.
        
        Args:
            path: Secret path to monitor
            callback: Callback function that receives the new secret value
            key: Optional key within the secret
        """
        cache_key = f"{path}:{key}" if key else path
        
        if cache_key not in self.refresh_callbacks:
            self.refresh_callbacks[cache_key] = []
            
        self.refresh_callbacks[cache_key].append(callback)
        self.logger.debug(f"Registered refresh callback for secret: {cache_key}")
        
    def start_auto_refresh(self, interval: int = 300):
        """
        Start auto-refresh of secrets.
        
        Args:
            interval: Refresh interval in seconds (default: 300 = 5 minutes)
        """
        if self._refresh_running:
            self.logger.warning("Auto-refresh already running")
            return
            
        self._refresh_interval = interval
        self._refresh_running = True
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True
        )
        self._refresh_thread.start()
        self.logger.info(f"Started auto-refresh with interval {interval}s")
        
    def stop_auto_refresh(self):
        """Stop auto-refresh of secrets."""
        if not self._refresh_running:
            return
            
        self._refresh_running = False
        if self._refresh_thread:
            self._refresh_thread.join(timeout=10)
            
        self.logger.info("Stopped auto-refresh")
        
    def _refresh_loop(self):
        """Background loop for refreshing secrets."""
        while self._refresh_running:
            time.sleep(self._refresh_interval)
            
            if not self._refresh_running:
                break
                
            self._refresh_secrets()
            
    def _refresh_secrets(self):
        """Refresh all cached secrets and call callbacks."""
        self.logger.debug("Refreshing secrets")
        
        for cache_key in list(self.cache.keys()):
            try:
                # Parse cache key
                parts = cache_key.split(':', 1)
                if len(parts) == 2:
                    path, key_str = parts
                    # Handle None vs string "None"
                    key = None if key_str == 'None' else key_str
                else:
                    path = cache_key
                    key = None
                    
                # Fetch new value
                new_value = self.backend.get_secret(path, key)
                old_value = self.cache.get(cache_key)
                
                # Update cache
                self.cache[cache_key] = new_value
                
                # Call callbacks if value changed
                if new_value != old_value and cache_key in self.refresh_callbacks:
                    for callback in self.refresh_callbacks[cache_key]:
                        try:
                            callback(new_value)
                        except Exception as e:
                            self.logger.error(f"Error in refresh callback: {e}", exc_info=True)
                            
            except Exception as e:
                self.logger.error(f"Error refreshing secret {cache_key}: {e}")
