# pyvdcapi - Outstanding Documentation Issues

**Last Updated:** 2026-02-09

This document tracks known documentation issues and improvement opportunities for the pyvdcapi library.

---

## 🔴 High Priority

No high-priority issues remaining.

---

## 🟡 Medium Priority

No medium-priority issues remaining.

---

## 🟢 Low Priority

No low-priority issues remaining.

---

## ✅ Recently Fixed

### ✅ Add Usage Examples to Button Component
- Added custom timing examples to Button class docstring
- Shows how to customize DOUBLE_PRESS_INTERVAL and LONG_PRESS_THRESHOLD
- Includes use cases for responsive UI and safety-critical actions
- Date: 2026-02-09

### ✅ Improve ServiceAnnouncer Documentation
- Updated module docstring with three clear usage patterns
- Updated class docstring with detailed async/sync examples
- Added warnings about context manager usage with asyncio event loops
- Clarified recommended usage (async) vs convenience methods (sync)
- Date: 2026-02-09

### ✅ Add Docstrings to Internal Methods
- `VdSD._initialize_common_states()`: Added detailed docstring listing all 3 states (operational, reachable, service)
- `VdSD._initialize_common_actions()`: Added detailed docstring explaining identify action with parameters
- `Vdc._load_vdsds()`: Enhanced existing docstring with complete restoration process
- `VdcHost._load_vdcs()`: Enhanced docstring explaining full hierarchy restoration
- Date: 2026-02-09

### ✅ Standardize Terminology
- Reviewed all markdown files for inconsistent capitalization
- Confirmed existing usage follows standard: "vDC" (prose), `Vdc` (code), `vdc` (files)
- All major documentation already consistent with recommendations
- Date: 2026-02-09

### ✅ Document model_uid Auto-generation
- Added comprehensive documentation to `VdcHost.create_vdc()` docstring
- Added comprehensive documentation to `Vdc.create_vdsd()` docstring
- Explains auto-generation from model name with examples
- Date: 2026-02-09

### ✅ ARCHITECTURE.md Message Handler Signatures
- Updated all VdcHost message handler signatures to match actual implementation
- All handlers now correctly documented as: `async def _handle_*(self, message: Message) -> Optional[Message]`
- Added `session` parameter to `_handle_generic_request` signature
- Added newly implemented utility methods: `get_vdc()`, `get_all_vdcs()`, `delete_vdc()`
- Date: 2026-02-09

### ✅ VdSD.configure() Method Documentation
- Added comprehensive documentation to API_REFERENCE.md
- Includes method signature, all configuration keys, and 4 detailed examples
- Examples cover: RGB light, climate sensor, motorized shade, YAML loading
- Date: 2026-02-09

### ✅ VdcHost Utility Methods
- Implemented: `get_vdc(dsuid)`, `get_all_vdcs()`, `delete_vdc(dsuid)`
- `delete_vdc()` also removes all associated vdSDs from persistence
- Date: 2026-02-09

### ✅ DSGroup.LIGHT → DSGroup.YELLOW
- Fixed in: `vdc_host.py`, `API_REFERENCE.md`
- Date: 2026-02-09

### ✅ Callback Function Signatures
- Fixed in: `API_REFERENCE.md`, `output_channel.py`, `vdsd.py`
- Changed from `callback(value)` to `callback(channel_type, value)`
- Date: 2026-02-09

### ✅ Invalid Method References
- Removed `toggle_output()` from examples
- Removed `output_function` parameter from `create_vdsd()` examples
- Date: 2026-02-09

---

## Future Enhancements (Not Issues)

These are ideas for expanding documentation, not bugs:

1. **Developer Guide** - Step-by-step walkthrough for creating custom devices
2. **Protocol Deep-Dive** - Detailed explanation of protobuf message flow
3. **Performance Guide** - Benchmarks and optimization tips
4. **Integration Examples** - Real smart home system integrations
5. **Pytest Test Suite** - Automated testing documentation
6. **API Changelog** - Track breaking changes between versions

---

## How to Contribute

If you're fixing one of these issues:

1. Check this file to understand the issue
2. Read DOCUMENTATION_REVIEW.md for context
3. Make your changes
4. Update this file to move issue to "Recently Fixed"
5. Submit PR with clear description

---

**Maintainer Notes:**
- Keep this file updated as issues are resolved
- Move fixed items to "Recently Fixed" with date
- Add new issues as discovered
- Review quarterly for stale items
