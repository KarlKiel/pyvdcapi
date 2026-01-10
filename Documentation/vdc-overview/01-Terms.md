# 1 Terms

| Term | Description |
|---|---|
| (logical) vDC | virtual device connector. A vDC is primarily a logical entity within the dS system and has its own dSUID. A vDC represents a type or class of external devices. |
| vDC host | network device offering a server socket for vdsm to connect to. One vDC host can host multiple logical vDCs, if the host supports multiple device classes. |
| vdSM | virtual digitalSTROM Meter. A vdSM can connect to one or several vDC hosts to connect one or several logical vDCs to the dS system. |
| vdSD | virtual digtalSTROM device. A vdSD represents a single device in the dS system, and behaves like a real digitalSTROM terminal block (dSD, digitalSTROM device) |
| vDC session | logical connection between a vdSM and a vDC host (representing one or multiple vDCs) |
