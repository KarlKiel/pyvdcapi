import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.network import service_announcement  # noqa: E402

print(f"service_announcement loaded from: {service_announcement.__file__}")

# Check if _start_zeroconf_async exists
sa = service_announcement.ServiceAnnouncer(port=8440, use_avahi=False)
print(f"ServiceAnnouncer methods: {[m for m in dir(sa) if not m.startswith('_')]}")
print(f"Has _start_zeroconf_async: {hasattr(sa, '_start_zeroconf_async')}")
