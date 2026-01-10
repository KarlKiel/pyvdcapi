# Project Restructuring - January 2026

## Changes Made

The project structure has been reorganized for better logical coherence and maintainability.

### Files Moved

1. **`pyvdcapi/actions.py` → `pyvdcapi/components/actions.py`**
   - **Rationale**: ActionManager, StateManager, and DevicePropertyManager are device components, so they belong in the `components/` folder alongside Output, Button, Sensor, etc.
   - **Impact**: More logical grouping with other device building blocks

2. **`pyvdcapi/constants.py` → `pyvdcapi/core/constants.py`**
   - **Rationale**: Constants are core domain definitions (DSGroup, DSScene, DSChannelType, etc.) and should be in the `core/` folder
   - **Impact**: Better separation of core domain logic from implementation

### Import Updates

All imports have been updated across the codebase:

#### Actions Module
- **Old**: `from pyvdcapi.actions import ...`
- **New**: `from pyvdcapi.components.actions import ...`

Updated files:
- `pyvdcapi/entities/vdsd.py` (2 imports)
- `examples/complete_protocol_demo.py` (1 import)
- `pyvdcapi/components/__init__.py` (exported in `__all__`)

#### Constants Module
- **Old**: `from pyvdcapi.constants import ...`
- **New**: `from pyvdcapi.core.constants import ...`

Updated files:
- `pyvdcapi/entities/vdsd.py`
- `pyvdcapi/entities/vdc_host.py`
- `pyvdcapi/components/output_channel.py`
- `pyvdcapi/components/output.py`
- `examples/motion_light_device.py`
- `examples/device_configuration.py`
- `examples/complete_protocol_demo.py`

### Module Exports Updated

1. **`pyvdcapi/components/__init__.py`**
   - Added exports: `ActionManager`, `StateManager`, `DevicePropertyManager`, `ActionParameter`
   - Now exports all device components in one place

2. **`pyvdcapi/core/__init__.py`**
   - Updated to export: `DSUIDGenerator`, `DSUIDNamespace`
   - Entities (VdcHost, Vdc, VdSD) moved to `entities/` folder

3. **`pyvdcapi/__init__.py`**
   - Updated imports to use `entities/` folder
   - Top-level API unchanged for backward compatibility

### New Project Structure

```
pyvdcapi/
├── __init__.py
├── core/                      # Core domain logic
│   ├── __init__.py
│   ├── constants.py           # ← MOVED HERE (from root)
│   └── dsuid.py
├── entities/                  # Main entities (vDC hierarchy)
│   ├── __init__.py
│   ├── vdc_host.py
│   ├── vdc.py
│   └── vdsd.py
├── components/                # Device components
│   ├── __init__.py
│   ├── actions.py             # ← MOVED HERE (from root)
│   ├── output.py
│   ├── output_channel.py
│   ├── button.py
│   ├── binary_input.py
│   └── sensor.py
├── network/                   # Protocol communication
│   ├── __init__.py
│   ├── tcp_server.py
│   ├── vdsm_session.py
│   └── message_router.py
├── properties/                # Property system
│   ├── __init__.py
│   ├── property_tree.py
│   ├── common.py
│   ├── vdc_props.py
│   └── vdsd_props.py
├── persistence/               # Data persistence
│   ├── __init__.py
│   └── yaml_store.py
└── utils/                     # Utilities
    ├── __init__.py
    ├── callbacks.py
    └── validators.py
```

### Rationale for Structure

**`core/`** - Fundamental building blocks
- `constants.py`: Domain constants (scenes, channels, groups)
- `dsuid.py`: Unique identifier generation

**`entities/`** - Main vDC hierarchy
- `vdc_host.py`: Top-level container
- `vdc.py`: Device collection
- `vdsd.py`: Individual device

**`components/`** - Device building blocks
- `actions.py`: Action/State/Property managers
- `output.py`, `output_channel.py`: Output control
- `button.py`, `binary_input.py`, `sensor.py`: Input components

**`network/`** - Communication layer
- TCP server, session management, message routing

**`properties/`** - Property system
- Property tree conversion, vDC/vdSD properties

**`persistence/`** - Data storage
- YAML persistence with shadow backup

**`utils/`** - Cross-cutting utilities
- Observable pattern, validators

### Benefits

1. **Better Organization**: Related files grouped together
2. **Clearer Dependencies**: Core → Entities → Components hierarchy
3. **Easier Navigation**: Logical folder structure
4. **Maintainability**: Changes to components don't affect core
5. **Discoverability**: New developers can understand structure faster

### Backward Compatibility

Top-level API remains unchanged:
```python
from pyvdcapi import VdcHost, Vdc, VdSD  # Still works!
```

Internal imports updated but external usage unaffected.

### Verification

All imports updated and verified:
- ✅ No broken imports
- ✅ All examples run correctly
- ✅ Module exports updated
- ✅ Documentation updated

### Files Modified

**Core Code** (10 files):
1. `pyvdcapi/__init__.py`
2. `pyvdcapi/core/__init__.py`
3. `pyvdcapi/components/__init__.py`
4. `pyvdcapi/entities/vdsd.py`
5. `pyvdcapi/entities/vdc_host.py`
6. `pyvdcapi/components/output_channel.py`
7. `pyvdcapi/components/output.py`
8. `pyvdcapi/components/actions.py` (internal imports)

**Examples** (3 files):
9. `examples/motion_light_device.py`
10. `examples/device_configuration.py`
11. `examples/complete_protocol_demo.py`

**Documentation** (1 file):
12. `README.md`

---

**Restructuring Complete**: January 10, 2026  
**All imports verified**: ✅  
**All examples tested**: ✅  
**Documentation updated**: ✅
