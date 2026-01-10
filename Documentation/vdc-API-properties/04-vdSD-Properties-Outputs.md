### 4.1.3 Outputs and Channels

Virtual devices in the digitalSTROM system can have a single output (or none at all, as for pure button devices). The output can have one or multiple channels. Outputs with complex functionality like color lights or blinds usually have multiple channels to control different aspects of the output separately

**Important Notes:**

- Devices with no output at all do not have output- and channel-related properties.
- Output is meant as "output functionality" - like a lamp, a blind, a washing machine. Such outputs may need multiple physical parameters to control, and thus will likely have multiple physical/electrical output lines. These multiple parameters do not count as separate outputs, but are called channels (of the single output, see below)
- If a physical device does have multiple, independent outputs (such as a multi-channel dimmer for example), a vDC must represent such a physical device as multiple virtual devices, with separate dSUIDs. The dSUID numbering scheme provides an enumeration field (17th byte) for that purpose.

For further notes on compatibility see 5.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| outputDescription | r | optional list of output description properties | Descriptions (invariable properties) of the device's output. Devices with no output don't have this property.<br>See 4.8.1 Output Descriptions for details |
| outputSettings | r/w | optional list of output settings properties | Settings (properties that can be changed and are stored persistently in the vDC) of the device's output. Devices with no output don't have this property.<br>See 4.8.2 Output Settings for details |
| outputState | r/w | optional list of output state properties | State (changing during operation of the device, but not persistently stored in the vDC) of the outputs. Devices with no output don't have this property.<br>See 4.8.3 Output States for details |
| channelDescriptions | r | optional list of property elements | Descriptions (invariable properties) of the channels in the device. See 4.9.1 Channel Descriptions for details |
| channelSettings | r/w | optional list of property elements | Settings (properties that can be changed and are stored persistently in the vDC) of the channels in the device.<br>See 4.9.2 Channel Settings for details |
| channelStates | r/w | optional list of property elements | State (changing during operation of the device, but not persistently stored in the vDC) of the channels.<br>See 4.9.3 Channel States for details |
