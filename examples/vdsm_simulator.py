"""
vdSM Simulator - Mock virtualSTROM Manager for testing vDC implementations.

This simulator acts as a vdSM (virtual digitalSTROM Manager) client that:
- Connects to a vDC host via TCP
- Performs the Hello handshake
- Discovers vDCs and devices (vdSDs)
- Queries properties
- Sends commands (scenes, output control, etc.)
- Displays all protocol communication

Usage:
    # Basic connection and discovery
    python examples/vdsm_simulator.py
    
    # Interactive mode
    python examples/vdsm_simulator.py --interactive
    
    # Automated test scenario
    python examples/vdsm_simulator.py --scenario full_test
"""

import asyncio
import sys
import os
import argparse
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from pyvdcapi.network import genericVDC_pb2 as pb
from pyvdcapi.network.genericVDC_pb2 import (
    Message,
    VDSM_REQUEST_HELLO,
    VDC_RESPONSE_HELLO,
    VDSM_REQUEST_GET_PROPERTY,
    VDC_RESPONSE_GET_PROPERTY,
    VDSM_REQUEST_GENERIC_REQUEST,
    GENERIC_RESPONSE,
    VDC_SEND_ANNOUNCE_VDC,
    VDC_SEND_ANNOUNCE_DEVICE,
    VDSM_NOTIFICATION_CALL_SCENE,
    VDSM_NOTIFICATION_SAVE_SCENE,
    VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE,
    VDSM_SEND_BYE,
)
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Information about a discovered device."""
    dsuid: str
    name: str
    model: str
    model_uid: str
    primary_group: int
    vdc_dsuid: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VdcInfo:
    """Information about a discovered vDC."""
    dsuid: str
    name: str
    model: str
    model_uid: str
    implementation_id: str
    devices: Dict[str, DeviceInfo] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)


class VdsmSimulator:
    """
    Simulates a vdSM (virtual digitalSTROM Manager) for testing vDC implementations.
    
    This class acts as a vdSM client that connects to a vDC host and performs
    all the typical operations a real vdSM would do.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 8444):
        """
        Initialize the vdSM simulator.
        
        Args:
            host: vDC host address
            port: vDC host port
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.message_id = 1
        
        # Discovered entities
        self.vdc_host_dsuid: Optional[str] = None
        self.vdc_host_name: Optional[str] = None
        self.vdcs: Dict[str, VdcInfo] = {}
        self.devices: Dict[str, DeviceInfo] = {}
        
    async def connect(self) -> bool:
        """
        Connect to the vDC host.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to vDC host at {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            logger.info("✓ Connected to vDC host")
            return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the vDC host."""
        if self.writer:
            try:
                # Send Bye message
                bye_msg = Message()
                bye_msg.type = VDSM_SEND_BYE
                await self._send_message(bye_msg)
                
                self.writer.close()
                await self.writer.wait_closed()
                logger.info("✓ Disconnected from vDC host")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
        
        self.connected = False
    
    def _get_next_message_id(self) -> int:
        """Get next message ID for correlation."""
        msg_id = self.message_id
        self.message_id += 1
        return msg_id
    
    async def _send_message(self, message: Message) -> None:
        """
        Send a protobuf message to the vDC host.
        
        Args:
            message: Message to send
        """
        # Serialize message
        data = message.SerializeToString()
        
        # Create header (4 bytes length, big-endian)
        header = len(data).to_bytes(4, byteorder='big')
        
        # Send header + data
        self.writer.write(header + data)
        await self.writer.drain()
        
        logger.debug(f"→ Sent message type {message.type}")
    
    async def _receive_message(self) -> Optional[Message]:
        """
        Receive a protobuf message from the vDC host.
        
        Returns:
            Received message or None if connection closed
        """
        try:
            # Read 4-byte header
            header = await self.reader.readexactly(4)
            length = int.from_bytes(header, byteorder='big')
            
            # Read message data
            data = await self.reader.readexactly(length)
            
            # Parse protobuf
            message = Message()
            message.ParseFromString(data)
            
            logger.debug(f"← Received message type {message.type}")
            return message
            
        except asyncio.IncompleteReadError:
            logger.warning("Connection closed by vDC host")
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None
    
    async def send_hello(self) -> bool:
        """
        Send Hello message to initiate session.
        
        Returns:
            True if Hello was successful
        """
        logger.info("\n" + "=" * 80)
        logger.info("HELLO HANDSHAKE")
        logger.info("=" * 80)
        
        # Create Hello request
        msg = Message()
        msg.type = VDSM_REQUEST_HELLO
        msg.message_id = self._get_next_message_id()
        
        msg.vdsm_request_hello.dSUID = "vdsm-simulator-001"
        
        logger.info(f"→ Sending Hello (dSUID: vdsm-simulator-001)")
        await self._send_message(msg)
        
        # Wait for response
        response = await self._receive_message()
        if not response or response.type != VDC_RESPONSE_HELLO:
            logger.error("✗ Did not receive Hello response")
            return False
        
        self.vdc_host_dsuid = response.vdc_response_hello.dSUID
        logger.info(f"← Received Hello response")
        logger.info(f"  vDC Host dSUID: {self.vdc_host_dsuid}")
        logger.info("✓ Handshake complete")
        
        return True
    
    async def get_property(self, dsuid: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get property from an entity (host/vDC/device).
        
        Args:
            dsuid: Entity dSUID (or empty string for host)
            query: Property query dict
            
        Returns:
            Property values or None if failed
        """
        from pyvdcapi.properties.property_tree import PropertyTree
        
        msg = Message()
        msg.type = VDSM_REQUEST_GET_PROPERTY
        msg.message_id = self._get_next_message_id()
        
        msg.vdsm_request_get_property.dSUID = dsuid
        msg.vdsm_request_get_property.query.extend(PropertyTree.to_protobuf(query))
        
        logger.debug(f"→ GetProperty for {dsuid or 'host'}: {list(query.keys())}")
        await self._send_message(msg)
        
        # Wait for response
        response = await self._receive_message()
        if not response or response.type != VDC_RESPONSE_GET_PROPERTY:
            logger.error("✗ Did not receive GetProperty response")
            return None
        
        # Parse properties
        properties = PropertyTree.from_protobuf(response.vdc_response_get_property.properties)
        logger.debug(f"← Received properties: {list(properties.keys())}")
        
        return properties
    
    async def discover_vdcs(self) -> List[str]:
        """
        Discover all vDCs on the host.
        
        Returns:
            List of vDC dSUIDs
        """
        logger.info("\n" + "=" * 80)
        logger.info("DISCOVERING vDCs")
        logger.info("=" * 80)
        
        # Get host properties first (includes name)
        host_props = await self.get_property("", {"dSUID": None, "name": None})
        if host_props:
            self.vdc_host_name = host_props.get('name', 'Unknown')
            logger.info(f"vDC Host: {self.vdc_host_name} ({self.vdc_host_dsuid})")
        
        # Generic request to announce vDCs
        msg = Message()
        msg.type = VDSM_REQUEST_GENERIC_REQUEST
        msg.message_id = self._get_next_message_id()
        
        msg.vdsm_request_generic_request.dSUID = ""
        msg.vdsm_request_generic_request.method_name = "getProperty"
        
        # Query for x-p44-vdcs container
        from pyvdcapi.properties.property_tree import PropertyTree
        msg.vdsm_request_generic_request.params.extend(
            PropertyTree.to_protobuf({"x-p44-vdcs": None})
        )
        
        logger.info("→ Requesting vDC list...")
        await self._send_message(msg)
        
        # Collect announcements
        vdc_dsuids = []
        while True:
            response = await asyncio.wait_for(self._receive_message(), timeout=2.0)
            
            if not response:
                break
            
            if response.type == VDC_SEND_ANNOUNCE_VDC:
                dsuid = response.vdc_send_announce_vdc.dSUID
                vdc_dsuids.append(dsuid)
                logger.info(f"  ← Announced vDC: {dsuid}")
                
            elif response.type == GENERIC_RESPONSE:
                # End of announcements
                logger.info(f"✓ Discovery complete: {len(vdc_dsuids)} vDC(s) found")
                break
        
        # Get detailed properties for each vDC
        for dsuid in vdc_dsuids:
            await self._get_vdc_details(dsuid)
        
        return vdc_dsuids
    
    async def _get_vdc_details(self, dsuid: str):
        """Get detailed properties for a vDC."""
        props = await self.get_property(dsuid, {
            "dSUID": None,
            "name": None,
            "model": None,
            "modelUID": None,
            "implementationId": None,
            "capabilities": None
        })
        
        if props:
            vdc_info = VdcInfo(
                dsuid=dsuid,
                name=props.get('name', 'Unknown'),
                model=props.get('model', 'Unknown'),
                model_uid=props.get('modelUID', 'Unknown'),
                implementation_id=props.get('implementationId', 'Unknown'),
                properties=props
            )
            self.vdcs[dsuid] = vdc_info
            
            logger.info(f"\n  vDC Details:")
            logger.info(f"    Name: {vdc_info.name}")
            logger.info(f"    Model: {vdc_info.model}")
            logger.info(f"    Implementation: {vdc_info.implementation_id}")
    
    async def discover_devices(self, vdc_dsuid: str) -> List[str]:
        """
        Discover all devices (vdSDs) in a vDC.
        
        Args:
            vdc_dsuid: vDC dSUID to query
            
        Returns:
            List of device dSUIDs
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"DISCOVERING DEVICES in vDC {vdc_dsuid}")
        logger.info("=" * 80)
        
        # Generic request to announce devices
        msg = Message()
        msg.type = VDSM_REQUEST_GENERIC_REQUEST
        msg.message_id = self._get_next_message_id()
        
        msg.vdsm_request_generic_request.dSUID = vdc_dsuid
        msg.vdsm_request_generic_request.method_name = "getProperty"
        
        # Query for x-p44-vdsds container
        from pyvdcapi.properties.property_tree import PropertyTree
        msg.vdsm_request_generic_request.params.extend(
            PropertyTree.to_protobuf({"x-p44-vdsds": None})
        )
        
        logger.info("→ Requesting device list...")
        await self._send_message(msg)
        
        # Collect announcements
        device_dsuids = []
        try:
            while True:
                response = await asyncio.wait_for(self._receive_message(), timeout=2.0)
                
                if not response:
                    break
                
                if response.type == VDC_SEND_ANNOUNCE_DEVICE:
                    dsuid = response.vdc_send_announce_device.dSUID
                    device_dsuids.append(dsuid)
                    logger.info(f"  ← Announced device: {dsuid}")
                    
                elif response.type == GENERIC_RESPONSE:
                    # End of announcements
                    logger.info(f"✓ Discovery complete: {len(device_dsuids)} device(s) found")
                    break
        except asyncio.TimeoutError:
            logger.info(f"✓ Discovery complete: {len(device_dsuids)} device(s) found")
        
        # Get detailed properties for each device
        for dsuid in device_dsuids:
            await self._get_device_details(dsuid, vdc_dsuid)
        
        return device_dsuids
    
    async def _get_device_details(self, dsuid: str, vdc_dsuid: str):
        """Get detailed properties for a device."""
        props = await self.get_property(dsuid, {
            "dSUID": None,
            "name": None,
            "model": None,
            "modelUID": None,
            "modelVersion": None,
            "displayId": None,
            "primaryGroup": None,
            "outputDescription": None,
            "inputDescriptions": None
        })
        
        if props:
            device_info = DeviceInfo(
                dsuid=dsuid,
                name=props.get('name', 'Unknown'),
                model=props.get('model', 'Unknown'),
                model_uid=props.get('modelUID', 'Unknown'),
                primary_group=props.get('primaryGroup', 0),
                vdc_dsuid=vdc_dsuid,
                properties=props
            )
            self.devices[dsuid] = device_info
            
            # Add to vDC's device list
            if vdc_dsuid in self.vdcs:
                self.vdcs[vdc_dsuid].devices[dsuid] = device_info
            
            logger.info(f"\n  Device Details:")
            logger.info(f"    Name: {device_info.name}")
            logger.info(f"    Model: {device_info.model}")
            logger.info(f"    Primary Group: {device_info.primary_group}")
            logger.info(f"    Display ID: {props.get('displayId', 'N/A')}")
            
            # Show outputs
            output_desc = props.get('outputDescription')
            if output_desc:
                logger.info(f"    Outputs: {output_desc}")
            
            # Show inputs
            input_descs = props.get('inputDescriptions')
            if input_descs:
                logger.info(f"    Inputs: {len(input_descs)} input(s)")
    
    async def call_scene(self, dsuid: str, scene: int, force: bool = False):
        """
        Call a scene on a device.
        
        Args:
            dsuid: Device dSUID
            scene: Scene number (0-255)
            force: Force call even if already in scene
        """
        logger.info(f"\n→ Calling scene {scene} on device {dsuid}")
        
        msg = Message()
        msg.type = VDSM_NOTIFICATION_CALL_SCENE
        
        msg.vdsm_notification_call_scene.dSUID = dsuid
        msg.vdsm_notification_call_scene.scene = scene
        msg.vdsm_notification_call_scene.force = force
        
        await self._send_message(msg)
        logger.info("✓ Scene call sent")
    
    async def set_output_value(self, dsuid: str, channel_type: int, value: float, 
                               transition_time: float = 0.0):
        """
        Set an output channel value.
        
        Args:
            dsuid: Device dSUID
            channel_type: Output channel type (0=brightness, 1=hue, etc.)
            value: Target value (0.0-100.0)
            transition_time: Transition time in seconds
        """
        logger.info(f"\n→ Setting output channel {channel_type} to {value}% on {dsuid}")
        
        msg = Message()
        msg.type = VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE
        
        msg.vdsm_notification_set_output_channel_value.dSUID = dsuid
        msg.vdsm_notification_set_output_channel_value.channel_type = channel_type
        msg.vdsm_notification_set_output_channel_value.value = value
        msg.vdsm_notification_set_output_channel_value.transition_time = transition_time
        msg.vdsm_notification_set_output_channel_value.apply_now = True
        
        await self._send_message(msg)
        logger.info("✓ Output value set")
    
    async def save_scene(self, dsuid: str, scene: int):
        """
        Save current state as a scene.
        
        Args:
            dsuid: Device dSUID
            scene: Scene number to save to
        """
        logger.info(f"\n→ Saving current state to scene {scene} on {dsuid}")
        
        msg = Message()
        msg.type = VDSM_NOTIFICATION_SAVE_SCENE
        
        msg.vdsm_notification_save_scene.dSUID = dsuid
        msg.vdsm_notification_save_scene.scene = scene
        
        await self._send_message(msg)
        logger.info("✓ Scene save sent")
    
    async def full_discovery(self):
        """Perform complete discovery of all entities."""
        logger.info("\n" + "=" * 80)
        logger.info("FULL DISCOVERY STARTING")
        logger.info("=" * 80)
        
        # Discover vDCs
        vdc_dsuids = await self.discover_vdcs()
        
        # Discover devices in each vDC
        for vdc_dsuid in vdc_dsuids:
            await self.discover_devices(vdc_dsuid)
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print a summary of all discovered entities."""
        logger.info("\n" + "=" * 80)
        logger.info("DISCOVERY SUMMARY")
        logger.info("=" * 80)
        
        logger.info(f"\nvDC Host: {self.vdc_host_name or 'Unknown'}")
        logger.info(f"  dSUID: {self.vdc_host_dsuid}")
        
        logger.info(f"\nvDCs: {len(self.vdcs)}")
        for vdc in self.vdcs.values():
            logger.info(f"\n  • {vdc.name}")
            logger.info(f"    dSUID: {vdc.dsuid}")
            logger.info(f"    Model: {vdc.model}")
            logger.info(f"    Devices: {len(vdc.devices)}")
            
            for device in vdc.devices.values():
                logger.info(f"\n      ◦ {device.name}")
                logger.info(f"        dSUID: {device.dsuid}")
                logger.info(f"        Model: {device.model}")
                logger.info(f"        Group: {device.primary_group}")
        
        logger.info(f"\nTotal Devices: {len(self.devices)}")
    
    async def run_interactive(self):
        """Run in interactive mode with user commands."""
        print("\n" + "=" * 80)
        print("vdSM SIMULATOR - Interactive Mode")
        print("=" * 80)
        print("\nCommands:")
        print("  discover        - Discover all vDCs and devices")
        print("  list            - Show discovered entities")
        print("  scene <dsuid> <num>  - Call scene on device")
        print("  set <dsuid> <ch> <val>  - Set output value")
        print("  quit            - Exit")
        print()
        
        while True:
            try:
                cmd = input("vdSM> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == 'quit':
                    break
                    
                elif cmd[0] == 'discover':
                    await self.full_discovery()
                    
                elif cmd[0] == 'list':
                    self._print_summary()
                    
                elif cmd[0] == 'scene' and len(cmd) == 3:
                    await self.call_scene(cmd[1], int(cmd[2]))
                    
                elif cmd[0] == 'set' and len(cmd) == 4:
                    await self.set_output_value(cmd[1], int(cmd[2]), float(cmd[3]))
                    
                else:
                    print("Unknown command")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='vdSM Simulator')
    parser.add_argument('--host', default='localhost', help='vDC host address')
    parser.add_argument('--port', type=int, default=8444, help='vDC host port')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--scenario', choices=['discovery', 'full_test'], 
                       default='discovery', help='Test scenario to run')
    
    args = parser.parse_args()
    
    # Create simulator
    sim = VdsmSimulator(host=args.host, port=args.port)
    
    try:
        # Connect
        if not await sim.connect():
            return 1
        
        # Handshake
        if not await sim.send_hello():
            return 1
        
        if args.interactive:
            # Interactive mode
            await sim.run_interactive()
        else:
            # Automated scenario
            if args.scenario == 'discovery' or args.scenario == 'full_test':
                await sim.full_discovery()
            
            if args.scenario == 'full_test':
                # Run some test commands if devices exist
                if sim.devices:
                    logger.info("\n" + "=" * 80)
                    logger.info("RUNNING TEST COMMANDS")
                    logger.info("=" * 80)
                    
                    # Get first device
                    device_dsuid = list(sim.devices.keys())[0]
                    
                    # Test scene call
                    await sim.call_scene(device_dsuid, 5)
                    await asyncio.sleep(1)
                    
                    # Test output control
                    await sim.set_output_value(device_dsuid, 0, 75.0, 2.0)
                    await asyncio.sleep(1)
                    
                    # Save scene
                    await sim.save_scene(device_dsuid, 1)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    finally:
        # Disconnect
        await sim.disconnect()
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
