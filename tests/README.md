# Tests

This directory contains test files for the pyvdcapi library.

## Test Files

- `test_simple.py` - Basic functionality test for VdcHost, Vdc, and VdSD creation
- `test_service_announcement.py` - Unit tests for the service announcement module
- `test_vdc_host_announcement.py` - Integration tests for VdcHost with service announcement

## Running Tests

From the repository root directory:

```bash
# Run individual test
python tests/test_simple.py
python tests/test_service_announcement.py
python tests/test_vdc_host_announcement.py

# Or use pytest (if installed)
pytest tests/
```

## Notes

- All test files automatically add the repository root to `sys.path`
- Service announcement tests will show warnings if `zeroconf` is not installed (this is expected)
- Tests are designed to run standalone without requiring external dependencies to be installed
