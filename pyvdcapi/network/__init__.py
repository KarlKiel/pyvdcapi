"""
Network layer components for vDC API communication.

This module provides the TCP networking infrastructure for the vDC API,
implementing the protocol's specific requirements:

- 2-byte length-prefixed message framing
- Asynchronous I/O for concurrent client handling
- Protocol buffer message encoding/decoding
- Connection management and lifecycle

Components:
- TCPServer: Asyncio-based TCP server with vDC protocol framing
- VdSMSession: Manages individual vdSM client connections
- MessageRouter: Routes incoming protobuf messages to handlers
"""
