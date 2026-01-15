"""
YAML persistence for vDC host, vDCs, and vdSDs.

Maintains configuration in property-tree format matching vDC API structure.

Shadow Backup Strategy:
- Creates .bak backup before each save
- Atomic write using temporary file + rename
- Validation after load to detect corruption
- Automatic recovery from backup on load failure
"""

import yaml
import os
import shutil
import tempfile
from typing import Dict, Any, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class YAMLPersistence:
    """
    YAML-based persistence for vDC API entities with shadow backup.
    
    Stores configuration in property-tree format for easy translation
    to/from vDC API PropertyElement messages.
    
    Backup Strategy:
    - Before each save, current file is backed up to .bak
    - New content is written to temporary file
    - Temporary file is atomically renamed to target file
    - On load failure, automatic fallback to .bak file
    """
    
    def __init__(self, file_path: str, auto_save: bool = True, enable_backup: bool = True):
        """
        Initialize YAML persistence.
        
        Args:
            file_path: Path to YAML file
            auto_save: If True, automatically save on updates
            enable_backup: If True, create .bak file before each save
        """
        self.file_path = file_path
        self.backup_path = file_path + '.bak'
        self.auto_save = auto_save
        self.enable_backup = enable_backup
        self._lock = Lock()
        self._data: Dict[str, Any] = {
            'vdc_host': {},
            'vdcs': {},
            'vdsds': {}
        }
        
        # Load existing data if file exists
        if os.path.exists(file_path):
            self.load()
        else:
            logger.info(f"Creating new persistence file: {file_path}")
    
    def load(self) -> None:
        """
        Load data from YAML file.
        
        If loading fails and backup exists, attempts to restore from backup.
        """
        with self._lock:
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data:
                        # Validate structure
                        if not isinstance(loaded_data, dict):
                            raise ValueError("Invalid YAML structure: root must be a dictionary")
                        self._data = loaded_data
                        # Normalize any vdsd keys that may be stored in
                        # non-canonical formats (e.g., stringified lists).
                        try:
                            if isinstance(self._data, dict) and 'vdsds' in self._data:
                                normalized = {}
                                for key, val in self._data.get('vdsds', {}).items():
                                    norm_key = self._normalize_dsuid(key)
                                    # Ensure val is a dict copy
                                    val_copy = val.copy() if isinstance(val, dict) else {'dSUID': str(val)}
                                    # Merge if multiple entries map to same canonical key
                                    if norm_key in normalized:
                                        existing = normalized[norm_key]
                                        existing.update(val_copy)
                                        existing['dSUID'] = norm_key
                                    else:
                                        val_copy['dSUID'] = norm_key
                                        normalized[norm_key] = val_copy
                                self._data['vdsds'] = normalized
                        except Exception:
                            # If normalization fails, continue with loaded data
                            pass
                logger.info(f"Loaded persistence from {self.file_path}")
            except Exception as e:
                # Try to restore from backup
                logger.error(f"Error loading YAML from {self.file_path}: {e}")
                if os.path.exists(self.backup_path):
                    logger.info(f"Attempting to restore from backup: {self.backup_path}")
                    try:
                        with open(self.backup_path, 'r', encoding='utf-8') as f:
                            loaded_data = yaml.safe_load(f)
                            if loaded_data:
                                self._data = loaded_data
                        logger.info("Successfully restored from backup")
                        # Save restored data to main file
                        self._save_internal()
                    except Exception as backup_error:
                        logger.error(f"Failed to restore from backup: {backup_error}", exc_info=True)
                        raise
                else:
                    logger.error("No backup file available for recovery")
                    raise
    
    def save(self) -> None:
        """Save data to YAML file with shadow backup."""
        with self._lock:
            self._save_internal()
    
    def _save_internal(self) -> None:
        """
        Internal save implementation (assumes lock is already held).
        
        Uses atomic write pattern:
        - Backup existing file to .bak
        - Write to temporary file in same directory
        - Atomic rename to target filename
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.file_path) or '.', exist_ok=True)
            
            # Create backup of existing file
            if self.enable_backup and os.path.exists(self.file_path):
                try:
                    shutil.copy2(self.file_path, self.backup_path)
                    logger.debug(f"Created backup: {self.backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Write to temporary file in same directory (for atomic rename)
            dir_path = os.path.dirname(self.file_path) or '.'
            temp_fd, temp_path = tempfile.mkstemp(
                dir=dir_path,
                prefix='.tmp_',
                suffix='.yaml',
                text=True
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(
                        self._data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False
                    )
                
                # Atomic rename (overwrites target)
                # On Windows, need to use os.replace for atomic overwrite
                os.replace(temp_path, self.file_path)
                logger.debug(f"Saved persistence to {self.file_path}")
                    
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
                
        except Exception as e:
            logger.error(f"Error saving YAML: {e}", exc_info=True)
            raise

    def _normalize_dsuid(self, dsuid: Any) -> str:
        """
        Normalize various dSUID representations into canonical string form.

        Handles:
        - bytes/str: return uppercased without separators
        - lists/tuples: take first element
        - stringified lists like "['abc']" -> extracts inner value
        """
        try:
            # If it's a sequence (list/tuple), take first element
            if isinstance(dsuid, (list, tuple)):
                dsuid_val = dsuid[0]
            else:
                dsuid_val = dsuid

            # Coerce to string
            dsuid_str = str(dsuid_val)

            # If string looks like a bracketed list: "['...']" or '["..."]'
            if dsuid_str.startswith('[') and dsuid_str.endswith(']'):
                inner = dsuid_str[1:-1].strip()
                if (inner.startswith("'") and inner.endswith("'")) or (inner.startswith('"') and inner.endswith('"')):
                    inner = inner[1:-1]
                dsuid_str = inner

            # Normalize formatting
            dsuid_str = dsuid_str.upper().replace('-', '').replace(':', '')
            return dsuid_str
        except Exception:
            return str(dsuid)
    
    def get_vdc_host(self) -> Dict[str, Any]:
        """Get vDC host configuration."""
        with self._lock:
            return self._data.get('vdc_host', {}).copy()
    
    def set_vdc_host(self, config: Dict[str, Any]) -> None:
        """
        Set vDC host configuration.
        
        Args:
            config: vDC host configuration dictionary
        """
        with self._lock:
            self._data['vdc_host'] = config
        
        if self.auto_save:
            self.save()
    
    def get_vdc(self, dsuid: str) -> Optional[Dict[str, Any]]:
        """
        Get vDC configuration by dSUID.
        
        Args:
            dsuid: dSUID of the vDC
            
        Returns:
            vDC configuration or None if not found
        """
        with self._lock:
            vdcs = self._data.get('vdcs', {})
            entry = vdcs.get(dsuid)
            if entry is None:
                return None
            return entry.copy()
    
    def set_vdc(self, dsuid: str, config: Dict[str, Any]) -> None:
        """
        Set vDC configuration.
        
        Args:
            dsuid: dSUID of the vDC
            config: vDC configuration dictionary
        """
        with self._lock:
            if 'vdcs' not in self._data:
                self._data['vdcs'] = {}
            self._data['vdcs'][dsuid] = config
        
        if self.auto_save:
            self.save()
    
    def delete_vdc(self, dsuid: str) -> bool:
        """
        Delete vDC configuration.
        
        Args:
            dsuid: dSUID of the vDC
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if dsuid in self._data.get('vdcs', {}):
                del self._data['vdcs'][dsuid]
                if self.auto_save:
                    self.save()
                return True
            return False
    
    def get_all_vdcs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all vDC configurations.
        
        Returns:
            Dictionary mapping dSUID to vDC configuration
        """
        with self._lock:
            return self._data.get('vdcs', {}).copy()
    
    def get_vdsd(self, dsuid: str) -> Optional[Dict[str, Any]]:
        """
        Get vdSD configuration by dSUID.
        
        Args:
            dsuid: dSUID of the vdSD
            
        Returns:
            vdSD configuration or None if not found
        """
        dsuid = self._normalize_dsuid(dsuid)
        with self._lock:
            vdsds = self._data.get('vdsds', {})
            entry = vdsds.get(dsuid)
            if entry is None:
                return None
            return entry.copy()
    
    def set_vdsd(self, dsuid: str, config: Dict[str, Any]) -> None:
        """
        Set vdSD configuration.
        
        Args:
            dsuid: dSUID of the vdSD
            config: vdSD configuration dictionary
        """
        dsuid = self._normalize_dsuid(dsuid)
        # Ensure stored config has canonical dSUID
        config = dict(config)
        config['dSUID'] = dsuid

        with self._lock:
            if 'vdsds' not in self._data:
                self._data['vdsds'] = {}
            self._data['vdsds'][dsuid] = config
        
        if self.auto_save:
            self.save()
    
    def delete_vdsd(self, dsuid: str) -> bool:
        """
        Delete vdSD configuration.
        
        Args:
            dsuid: dSUID of the vdSD
            
        Returns:
            True if deleted, False if not found
        """
        dsuid = self._normalize_dsuid(dsuid)
        with self._lock:
            if dsuid in self._data.get('vdsds', {}):
                del self._data['vdsds'][dsuid]
                if self.auto_save:
                    self.save()
                return True
            return False
    
    def get_all_vdsds(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all vdSD configurations.
        
        Returns:
            Dictionary mapping dSUID to vdSD configuration
        """
        with self._lock:
            return self._data.get('vdsds', {}).copy()
    
    def get_vdsds_for_vdc(self, vdc_dsuid: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all vdSDs belonging to a specific vDC.
        
        Args:
            vdc_dsuid: dSUID of the vDC
            
        Returns:
            Dictionary mapping dSUID to vdSD configuration
        """
        with self._lock:
            result = {}
            for dsuid, config in self._data.get('vdsds', {}).items():
                if config.get('vdc_dSUID') == vdc_dsuid:
                    result[dsuid] = config.copy()
            return result
    
    def update_vdsd_property(self, dsuid: str, property_path: str, value: Any) -> None:
        """
        Update a specific property of a vdSD.
        
        Args:
            dsuid: dSUID of the vdSD
            property_path: Dot-separated property path (e.g., "outputs.0.value")
            value: New value
        """
        dsuid = self._normalize_dsuid(dsuid)

        with self._lock:
            if 'vdsds' not in self._data:
                self._data['vdsds'] = {}

            if dsuid not in self._data.get('vdsds', {}):
                logger.warning(f"vdSD {dsuid} not found in persistence; creating new entry")
                # Create minimal vdSD entry so nested properties can be set
                self._data['vdsds'][dsuid] = {'dSUID': dsuid}

            config = self._data['vdsds'][dsuid]
            parts = property_path.split('.')
            current = config
            
            # Navigate to the parent of the target property
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the final value
            current[parts[-1]] = value
        
        if self.auto_save:
            self.save()
    
    def clear_all(self) -> None:
        """Clear all data (use with caution)."""
        with self._lock:
            self._data = {
                'vdc_host': {},
                'vdcs': {},
                'vdsds': {}
            }
        
        if self.auto_save:
            self.save()
