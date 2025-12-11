"""Configuration hot-reload support for Mira platform."""
import os
import json
import logging
import threading
from typing import Callable, List, Dict, Any, Optional
from pathlib import Path


class ConfigWatcher:
    """
    Watches configuration files for changes and triggers reload callbacks.
    
    Uses watchdog library if available, otherwise falls back to polling.
    """
    
    def __init__(self, config_path: str, poll_interval: int = 5):
        """
        Initialize configuration watcher.
        
        Args:
            config_path: Path to configuration file to watch
            poll_interval: Polling interval in seconds (used when watchdog unavailable)
        """
        self.logger = logging.getLogger("mira.config.watcher")
        self.config_path = config_path
        self.poll_interval = poll_interval
        self.reload_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.running = False
        self.observer = None
        self.poll_thread = None
        self.last_modified = 0
        self.use_watchdog = False
        
        # Try to use watchdog if available
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            self.use_watchdog = True
            self.logger.info("Using watchdog for configuration monitoring")
        except ImportError:
            self.logger.info("watchdog not available, using polling for configuration monitoring")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback to be called when configuration changes.
        
        Args:
            callback: Function that accepts the new configuration dict
        """
        self.reload_callbacks.append(callback)
        self.logger.debug(f"Registered reload callback: {callback.__name__}")
    
    def start(self):
        """Start watching the configuration file."""
        if self.running:
            return
        
        self.running = True
        
        if not os.path.exists(self.config_path):
            self.logger.warning(f"Configuration file does not exist: {self.config_path}")
            return
        
        self.last_modified = os.path.getmtime(self.config_path)
        
        if self.use_watchdog:
            self._start_watchdog()
        else:
            self._start_polling()
        
        self.logger.info(f"Started watching configuration file: {self.config_path}")
    
    def stop(self):
        """Stop watching the configuration file."""
        if not self.running:
            return
        
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        if self.poll_thread:
            self.poll_thread.join(timeout=self.poll_interval + 1)
        
        self.logger.info("Stopped watching configuration file")
    
    def _start_watchdog(self):
        """Start file watching using watchdog library."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, parent):
                self.parent = parent
            
            def on_modified(self, event):
                if not event.is_directory and event.src_path == self.parent.config_path:
                    self.parent._handle_file_change()
        
        self.observer = Observer()
        event_handler = ConfigFileHandler(self)
        watch_dir = str(Path(self.config_path).parent)
        self.observer.schedule(event_handler, watch_dir, recursive=False)
        self.observer.start()
    
    def _start_polling(self):
        """Start file watching using polling."""
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
    
    def _poll_loop(self):
        """Polling loop to check for file changes."""
        import time
        
        while self.running:
            try:
                time.sleep(self.poll_interval)
                
                if not os.path.exists(self.config_path):
                    continue
                
                current_modified = os.path.getmtime(self.config_path)
                if current_modified > self.last_modified:
                    self.last_modified = current_modified
                    self._handle_file_change()
            
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
    
    def _handle_file_change(self):
        """Handle configuration file change."""
        try:
            # Add a small delay to ensure file write is complete
            import time
            time.sleep(0.1)
            
            self.logger.info(f"Configuration file changed: {self.config_path}")
            
            # Load new configuration
            with open(self.config_path, 'r') as f:
                new_config = json.load(f)
            
            # Call all registered callbacks
            for callback in self.reload_callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    self.logger.error(f"Error in reload callback {callback.__name__}: {e}", exc_info=True)
        
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}", exc_info=True)


class HotReloadableConfig:
    """
    Configuration class with hot-reload support.
    
    Wraps the Config class to add file watching and automatic reloading.
    """
    
    def __init__(self, config_instance, config_path: Optional[str] = None, 
                 enable_hot_reload: bool = True, poll_interval: int = 5):
        """
        Initialize hot-reloadable configuration.
        
        Args:
            config_instance: Existing Config instance to wrap
            config_path: Path to configuration file
            enable_hot_reload: Whether to enable hot-reload (default: True)
            poll_interval: Polling interval in seconds for fallback mode
        """
        self.logger = logging.getLogger("mira.config.hotreload")
        self.config = config_instance
        self.config_path = config_path
        self.watcher = None
        self.reload_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        if enable_hot_reload and config_path and os.path.exists(config_path):
            self.watcher = ConfigWatcher(config_path, poll_interval)
            self.watcher.register_callback(self._on_config_reload)
            self.watcher.start()
            self.logger.info("Hot-reload enabled for configuration")
    
    def _on_config_reload(self, new_config: Dict[str, Any]):
        """
        Handle configuration reload.
        
        Args:
            new_config: New configuration dictionary
        """
        self.logger.info("Reloading configuration...")
        
        # Update the config instance
        old_config = self.config.config_data.copy()
        self.config.config_data = new_config
        
        # Re-apply environment variable overrides using public method
        self.config.reload_from_env()
        
        # Call user-registered callbacks
        for callback in self.reload_callbacks:
            try:
                callback(self.config.config_data)
            except Exception as e:
                self.logger.error(f"Error in user reload callback: {e}", exc_info=True)
        
        self.logger.info("Configuration reloaded successfully")
    
    def register_reload_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback to be called when configuration is reloaded.
        
        Args:
            callback: Function that accepts the new configuration dict
        """
        self.reload_callbacks.append(callback)
    
    def stop_watching(self):
        """Stop watching for configuration changes."""
        if self.watcher:
            self.watcher.stop()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config.set(key, value)


def enable_hot_reload(config_instance, config_path: Optional[str] = None,
                     poll_interval: int = 5) -> HotReloadableConfig:
    """
    Enable hot-reload for a Config instance.
    
    Args:
        config_instance: Existing Config instance
        config_path: Path to configuration file
        poll_interval: Polling interval in seconds
        
    Returns:
        HotReloadableConfig instance wrapping the original config
    """
    return HotReloadableConfig(config_instance, config_path, True, poll_interval)
