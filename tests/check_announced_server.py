"""
Check what server name is actually being announced on the network
"""

from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import time


class VdcListener(ServiceListener):
    def add_service(self, zc, type_, name):
        if "PyVDC" in name:
            info = zc.get_service_info(type_, name)
            if info:
                print(f"\n{'='*70}")
                print("FOUND YOUR VDC HOST!")
                print(f"{'='*70}")
                print(f"Name:    {name}")
                print(f"Server:  {info.server} ← THIS MUST BE LOWERCASE!")
                print(f"Port:    {info.port}")
                addrs = [".".join(str(b) for b in addr) for addr in info.addresses]
                print(f"IPs:     {', '.join(addrs)}")
                print(f"{'='*70}\n")

                if info.server != info.server.lower():
                    print(" WARNING: Server name is NOT lowercase!")
                    print(f" Expected: {info.server.lower()}")
                    print(f" Got:      {info.server}")
                else:
                    print(" ✓ Server name IS lowercase - Good for Avahi!")
                print()

    def remove_service(self, zc, type_, name):
        pass

    def update_service(self, zc, type_, name):
        pass


print("\nListening for your vDC host announcement...")
print("Make sure your vDC host is running!")
print("Scanning for 15 seconds...\n")

zc = Zeroconf()
listener = VdcListener()
browser = ServiceBrowser(zc, "_ds-vdc._tcp.local.", listener)

time.sleep(15)

print("\nDone.\n")
zc.close()
