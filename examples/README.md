# Examples

This folder contains runnable examples that demonstrate how to use the `pyvdcapi` library.

Files:

- `service_announcement_demo.py` — full demo that creates a host, vDC and devices and announces via mDNS.
- `example_clean_start.py` — interactive script to create and start a `VdcHost` and enable service announcement.
- `discover.py` — discovery helper that prints discovered `_ds-vdc._tcp.local.` services with properties.

Requirements:

Create a virtual environment and install the minimal requirements:

```bash
python3 -m venv /path/to/venv
. /path/to/venv/bin/activate
pip install --upgrade pip
pip install -r examples/requirements.txt
```

Running `example_clean_start.py`:

```bash
python3 examples/example_clean_start.py
```

The script will prompt for host details, start the `VdcHost` with service announcement enabled, and run until you press Ctrl+C.
