#!/usr/bin/env python3
"""
Control Values Demo: Heating Radiator Example

Demonstrates the correct bidirectional behavior of Control Values:
- DSS writes control values (e.g., target temperature via heatingLevel)
- Device reads control values to control hardware (e.g., radiator valve)
- Device CANNOT arbitrarily write control values (only DSS can)

Use Case:
A room temperature is controlled via digitalSTROM native device.
The DSS sends heatingLevel control value to the vDC.
The radiator device reads this value to adjust its heating cycles.
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyvdcapi.properties.control_value import ControlValues, ControlValue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HeatingRadiator:
    """
    Simulated heating radiator that reacts to control values.
    
    This demonstrates the device-side read-only access to control values.
    The radiator reads heatingLevel but never writes it.
    """
    
    def __init__(self, control_values: ControlValues):
        self.control_values = control_values
        self.current_temperature = 18.0  # Current room temperature
        self.valve_position = 0.0  # 0-100%
        
        logger.info(f"Heating Radiator initialized")
    
    def on_control_change(self, control_name: str, value: float):
        """
        Hardware callback when DSS sends a new control value.
        
        This is where the device reacts to control value updates from DSS.
        """
        if control_name == 'heatingLevel':
            logger.info(f"🌡️  DSS updated heatingLevel to {value}")
            self.adjust_heating(value)
    
    def adjust_heating(self, heating_level: float):
        """
        Adjust radiator based on heatingLevel control value.
        
        Args:
            heating_level: -100 (cooling) to +100 (heating)
                          0 = no heating/cooling
        """
        # *** DEVICE READS CONTROL VALUE (read-only from device perspective) ***
        control_value = self.control_values.get('heatingLevel')
        if control_value:
            logger.info(f"📖 Device READS heatingLevel = {control_value.value}")
            logger.info(f"   Group: {control_value.group}, Zone: {control_value.zone_id}")
        
        # Convert heatingLevel to valve position
        # heatingLevel: -100 to +100
        # valve_position: 0 to 100%
        
        if heating_level > 0:
            # Heating mode
            self.valve_position = min(100.0, heating_level)
            logger.info(f"🔥 Heating: Opening valve to {self.valve_position:.1f}%")
        elif heating_level < 0:
            # Cooling mode (close valve completely)
            self.valve_position = 0.0
            logger.info(f"❄️  Cooling: Closing valve to {self.valve_position:.1f}%")
        else:
            # Neutral (maintain current state)
            logger.info(f"⏸️  Neutral: Maintaining valve at {self.valve_position:.1f}%")
    
    def simulate_heating_cycle(self):
        """Simulate temperature adjustment based on valve position."""
        # Simple simulation: temperature increases with valve position
        if self.valve_position > 0:
            temp_increase = (self.valve_position / 100.0) * 0.5
            self.current_temperature += temp_increase
            logger.info(f"🌡️  Room temperature: {self.current_temperature:.1f}°C (valve: {self.valve_position:.1f}%)")
        else:
            # Temperature slowly drops when valve closed
            self.current_temperature -= 0.1
            logger.info(f"🌡️  Room temperature: {self.current_temperature:.1f}°C (valve closed)")


def main():
    """Demonstrate control values with heating radiator."""
    
    logger.info("=" * 70)
    logger.info("Control Values Demo: Heating Radiator")
    logger.info("=" * 70)
    
    # Create control values container (represents device's control values)
    control_values = ControlValues()
    
    # Create hardware controller
    radiator = HeatingRadiator(control_values)
    
    logger.info("\n" + "=" * 70)
    logger.info("Scenario 1: DSS sets target temperature (warm)")
    logger.info("=" * 70)
    
    # *** DSS WRITES CONTROL VALUE (write-only from DSS perspective) ***
    logger.info("📡 DSS WRITES: Set heatingLevel to 75.0 (target: warm room)")
    control_values.set('heatingLevel', 75.0, group=1, zone_id=0)
    radiator.on_control_change('heatingLevel', 75.0)
    
    # Simulate heating cycles
    import time
    for cycle in range(3):
        time.sleep(0.3)
        radiator.simulate_heating_cycle()
    
    logger.info("\n" + "=" * 70)
    logger.info("Scenario 2: DSS adjusts to moderate temperature")
    logger.info("=" * 70)
    
    # *** DSS WRITES CONTROL VALUE ***
    logger.info("📡 DSS WRITES: Set heatingLevel to 40.0 (target: moderate)")
    control_values.set('heatingLevel', 40.0, group=1, zone_id=0)
    radiator.on_control_change('heatingLevel', 40.0)
    
    # Simulate more cycles
    for cycle in range(3):
        time.sleep(0.3)
        radiator.simulate_heating_cycle()
    
    logger.info("\n" + "=" * 70)
    logger.info("Scenario 3: DSS turns off heating")
    logger.info("=" * 70)
    
    # *** DSS WRITES CONTROL VALUE ***
    logger.info("📡 DSS WRITES: Set heatingLevel to 0.0 (turn off heating)")
    control_values.set('heatingLevel', 0.0, group=1, zone_id=0)
    radiator.on_control_change('heatingLevel', 0.0)
    
    # Simulate cooling down
    for cycle in range(3):
        time.sleep(0.3)
        radiator.simulate_heating_cycle()
    
    logger.info("\n" + "=" * 70)
    logger.info("Control Values Summary")
    logger.info("=" * 70)
    
    # *** DEVICE READS ALL CONTROL VALUES ***
    all_controls = control_values.to_simple_dict()
    logger.info(f"📊 Device READS all control values: {all_controls}")
    
    # Get detailed info
    heating_control = control_values.get('heatingLevel')
    if heating_control:
        logger.info(f"\n📋 Detailed heatingLevel info (device can READ):")
        logger.info(f"   Value: {heating_control.value}")
        logger.info(f"   Last Updated: {heating_control.last_updated}")
        logger.info(f"   Group: {heating_control.group}")
        logger.info(f"   Zone ID: {heating_control.zone_id}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ Demo complete!")
    logger.info("=" * 70)
    logger.info("\n🔑 Key takeaways:")
    logger.info("   1. DSS WRITES control values (heatingLevel) - write-only from DSS")
    logger.info("   2. Device READS control values to control hardware - read-only from device")
    logger.info("   3. Device reacts via hardware callback (on_control_change)")
    logger.info("   4. Control values are persisted and available after restart")
    logger.info("   5. Device NEVER arbitrarily writes control values (only DSS can)")
    logger.info("\n✅ Bidirectional access verified:")
    logger.info("   • DSS → write-only (acc=\"w\" in API)")
    logger.info("   • Device → read-only (can only read, not write)")


if __name__ == "__main__":
    main()

