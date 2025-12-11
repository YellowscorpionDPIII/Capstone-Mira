"""Configuration hot-reload support for the Mira platform."""
import os
import logging
import threading
from typing import Callable, List, Optional, Dict, Any
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class ConfigFileHandler(FileSystemEventHandler):
    """Handler for configuration file changes."""
    
    def __init__(self, config_path: str, reload_callback: Callable):
        """
        Initialize config file handler.
        
        Args:
            config_path: Path to configuration file to watch
            reload_callback: Callback to execute when config changes
        """
        super().__init__()
        self.config_path = Path(config_path).resolve()
        self.reload_callback = reload_callback
        self.logger = logging.getLogger("mira.config.watcher")
        
    def on_modified(self, event: FileSystemEvent):
        """
        Handle file modification events.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
            
        modified_path = Path(event.src_path).resolve()
        
        # Check if the modified file is our config file
        if modified_path == self.config_path:
            self.logger.info(f"Configuration file changed: {self.config_path}")
            try:
                self.reload_callback()
                self.logger.info("Configuration reloaded successfully")
            except Exception as e:
                self.logger.error(f"Error reloading configuration: {e}", exc_info=True)


class ConfigWatcher:
    """
    Watches configuration files for changes and reloads them.
    
    Uses the watchdog library to monitor file system events.
    """
    
    def __init__(self, config_path: str, reload_callback: Callable):
        """
        Initialize config watcher.
        
        Args:
            config_path: Path to configuration file to watch
            reload_callback: Callback to execute when config changes
        """
        self.config_path = Path(config_path).resolve()
        self.reload_callback = reload_callback
        self.logger = logging.getLogger("mira.config.watcher")
        
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[ConfigFileHandler] = None
        self.started = False
        self._lock = threading.Lock()
        
    def start(self):
        """Start watching the configuration file."""
        with self._lock:
            if self.started:
                self.logger.warning("Config watcher already started")
                return
                
            if not self.config_path.exists():
                self.logger.error(f"Configuration file does not exist: {self.config_path}")
                return
                
            # Watch the directory containing the config file
            watch_dir = self.config_path.parent
            
            self.event_handler = ConfigFileHandler(str(self.config_path), self.reload_callback)
            self.observer = Observer()
            self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
            self.observer.start()
            
            self.started = True
            self.logger.info(f"Started watching configuration file: {self.config_path}")
            
    def stop(self):
        """Stop watching the configuration file."""
        with self._lock:
            if not self.started:
                return
                
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                
            self.started = False
            self.logger.info("Stopped watching configuration file")
            
    def is_running(self) -> bool:
        """
        Check if the watcher is running.
        
        Returns:
            True if watcher is running
        """
        return self.started


class HotReloadConfig:
    """
    Configuration manager with hot-reload support.
    
    Extends the base configuration with file watching and automatic reload.
    """
    
    def __init__(self, config_instance, config_path: str):
        """
        Initialize hot-reload config.
        
        Args:
            config_instance: The configuration instance to reload
            config_path: Path to configuration file
        """
        self.config_instance = config_instance
        self.config_path = config_path
        self.watcher: Optional[ConfigWatcher] = None
        self.reload_callbacks: List[Callable] = []
        self.logger = logging.getLogger("mira.config.hotreload")
        
    def register_reload_callback(self, callback: Callable, name: Optional[str] = None):
        """
        Register a callback to be called after configuration reload.
        
        Args:
            callback: Function to call after config reload
            name: Optional name for the callback
        """
        callback_name = name or getattr(callback, '__name__', 'unknown')
        self.reload_callbacks.append((callback, callback_name))
        self.logger.debug(f"Registered reload callback: {callback_name}")
        
    def unregister_reload_callback(self, callback: Callable):
        """
        Unregister a reload callback.
        
        Args:
            callback: Callback to remove
        """
        self.reload_callbacks = [
            (cb, name) for cb, name in self.reload_callbacks if cb != callback
        ]
        
    def _reload_config(self):
        """Internal method to reload configuration."""
        self.logger.info("Reloading configuration")
        
        try:
            # Try common reload methods
            if hasattr(self.config_instance, 'reload'):
                # Preferred: use a standard reload method
                self.config_instance.reload()
            elif hasattr(self.config_instance, '_load_from_file'):
                # Fallback: use _load_from_file if available
                self.config_instance._load_from_file(self.config_path)
            elif hasattr(self.config_instance, 'load_yaml_config'):
                # Fallback: use load_yaml_config if available
                self.config_instance.load_yaml_config()
            else:
                self.logger.warning(
                    "Config instance does not have a supported reload method. "
                    "Please implement 'reload()', '_load_from_file(path)', or 'load_yaml_config()'"
                )
                return
                
            # Execute reload callbacks
            for callback, name in self.reload_callbacks:
                try:
                    self.logger.debug(f"Executing reload callback: {name}")
                    callback()
                except Exception as e:
                    self.logger.error(f"Error in reload callback {name}: {e}", exc_info=True)
                    
        except Exception as e:
            self.logger.error(f"Error reloading configuration: {e}", exc_info=True)
            
    def enable_hot_reload(self):
        """Enable hot-reload for the configuration file."""
        if not os.path.exists(self.config_path):
            self.logger.error(f"Configuration file does not exist: {self.config_path}")
            return
            
        self.watcher = ConfigWatcher(self.config_path, self._reload_config)
        self.watcher.start()
        self.logger.info(f"Hot-reload enabled for: {self.config_path}")
        
    def disable_hot_reload(self):
        """Disable hot-reload for the configuration file."""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
            self.logger.info("Hot-reload disabled")
            
    def is_hot_reload_enabled(self) -> bool:
        """
        Check if hot-reload is enabled.
        
        Returns:
            True if hot-reload is enabled
        """
        return self.watcher is not None and self.watcher.is_running()
