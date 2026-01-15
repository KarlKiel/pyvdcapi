import sys
from pathlib import Path

# Ensure the repository root is on sys.path regardless of where this script is located.
# When moved into tests/, Path(__file__).parent is tests/; parents[1] is repository root.
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from pyvdcapi.network import service_announcement
print(f"service_announcement loaded from: {service_announcement.__file__}")

# Check if _start_zeroconf_async exists
sa = service_announcement.ServiceAnnouncer(port=8440, use_avahi=False)
print(f"ServiceAnnouncer methods: {[m for m in dir(sa) if not m.startswith('_')]}")
print(f"Has _start_zeroconf_async: {hasattr(sa, '_start_zeroconf_async')}")
