"""
Quick diagnostic to check what server name is being announced
"""
import socket

hostname = socket.gethostname()
print(f"\nSystem hostname: {hostname}")
print(f"Lowercase: {hostname.lower()}")
print(f"Server name that should be used: {hostname.lower()}.local.")
print(f"\nFor Avahi compatibility, the server field in mDNS MUST use lowercase.")
print(f"Check your service_announcement.py line 140:")
print(f"  server_name = f\"{{self.host_name.lower()}}.local.\"")
print()
