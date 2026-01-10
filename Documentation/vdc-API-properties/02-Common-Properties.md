# 2 Common properties for all addressable entities

- The common properties must be supported by entities which can be addressed via a dSUID using this API (addressable entities). At the time of writing, this includes virtual devices, logical vDCs and the vDC host, but may be extended to other entities.
- The "type" property reveals the kind of entity.
- Properties common to a specific entity type are maintained in separate documents. In particular, see "vdSD properties" document for common properties of virtual devices.
- All names and fields are language independent, e.g. they must not change if the user selected a different system language on the VDC host system.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| dSUID | r | string of 34 hex characters (2*17) | the dSUID of the entity. Normally not used in regular vDC API calls, as these require the dSUID in the getProperty() call. Useful for debugging. |
| displayId | r | string | Human-readable identification usually printed on the physical device to identify the device, if available. |
| type | r | string | Type of entity:<br>"vdSD" : virtual dS device<br>"vDC" : a logical vDC<br>"vDChost" : the vDC host<br>"vdSM" : a vdSM |
| model | r | string | Human-readable model string of the entity. Should be descriptive enough to allow a human to associate it with a kind of hardware or software. Is mapped to "hardwareInfo" in vdsm and upstream |
| modelVersion | r | string | Human-readable model version string of the device, if available |
| modelUID | r | string | digitalSTROM system unique ID for the functional model of the entity.<br>• modelUID must be equal between all functionally identical entities (especially, devices) dS system.<br>• If different connected hardware devices provide EXACTLY the same dS functionality, these devices MAY have the same modelUID but will have different hardwareModelGuid.<br>• Vice versa, for example two identical hardware input devices will have the same hardwareModelGuid, but different modelUID if one input is mapped as a button, and the other as a binaryInput. |
| modelVersion | r | optional string | string describing the model's version as seen by the end user (usually the firmware version of the vdc host) |
| hardwareVersion | r | optional string | Human-readable string describing the hardware device's version represented by this entity, if available |
| hardwareGuid | r | optional string | hardware's native globally unique identifier (GUID), if any, in URN-like format: formatname:actualID<br><br>The following formats are in use:<br>• gs1:(01)ggggg(21)sssss = GS.1 formatted GTIN plus serial number<br>• macaddress:MMMMM = MAC Address<br>• enoceanaddress:XXXXXXXX = 8 hex digits EnOcean device address<br>• uuid:UUUUUUU = UUID |
| hardwareModelGuid | r | optional string | hardware model's native globally unique identification, if any, in URN-like format: formatname:actualID<br><br>The following formats are in use:<br>• gs1:(01)ggggg = GS.1 formatted GTIN<br>• enoceaneep:oofftt = 6 hex digits EnOcean Equipment Profile (EEP) number |
| vendorName | r | optional string | Human-readable string of the device manufacturer or vendor |
| vendorGuid | r | optional string | globally unique identification of the vendor, in URN-like format:<br>The following formats are in use:<br>• enoceanvendor:vvv[:name] = 3 hex digits EnOcean vendor ID, optionally followed by a colon and the clear text vendor name if known<br>• vendorname:name = clear text name of the vendor<br>• gs1:(412)lllll = GS1 formatted Global Location Number of the vendor |
| oemGuid | r | optional string | Globaly unique identifier (GUID) of the product the hardware is embedded in, if any - see hardwareGuid for format variants. |
| oemModelGuid | r | optional string | Globaly unique identifier (GUID) of the product model (if any) in gs1:(01)ggggggggggggg format. Often refered to as GTIN. |
| configURL | r | optional string | full URL how to reach the web configuration of this device (if any) |
| deviceIcon16 | r | optional binary png image | 16x16 pixel png image to represent this device in the digitalSTROM configurator UI |
| deviceIconName | r | optional string | filename-safe name for the icon (a-z, 0-9, _, -, no spaces or funny characters!). This allows for more efficient caching in Web UIs - many devices might have the same icon, so web UIs don't need to load the actual data (deviceIcon16) for every device again, as long as devices show the same deviceIconName. |
| name | r/w | string | user-specified name of the entity. Is also stored upstreams in the vdSM and further up, but is useful for the vDC to know for configuration and debugging.<br><br>The vDC usually generates descriptive default names for newly connected devices. When the vdSM registers a device, it should read this property and propagate the name towards the dSS. When the user changes the name via the dSS configurator, this property should be updated with the new name. |
| deviceClass | r | optional string | digitalSTROM defined unique name of a device class profile |
| deviceClassVersion | r | optional string | revision number of the device class profile |
| active | r | optional boolean | operation state of the addressable entity. If this is not true, this means the associated hardware cannot operate normally at this time. This might be due to communication problems, radio range limitations, missing configuration etc.<br><br>When a vDC detects a change in active, this will be reported to vDC API clients via pushProperty. However, vDCs cannot guarantee timely updates of active in all cases. In particular, detecting hardware becoming disconnected or no longer reachable might involve long timeouts or might not be feasible at all, depending on the hardware type.<br><br>Note: active is optional only to maintain backwards compatibility with earlier versions of this specification. Still, active should be implemented in all modern vDCs.<br><br>Note: active does not replace the ping/pong mechanism that always could be used to poll the operation state. ping/pong must be implemented in all vDCs. |

## Identification Properties in the vDC API

|  | device instance | device model | device class | Format |
|---|---|---|---|---|
| System IDs | dSUID |  | modelGUID<br>deviceClass<br>deviceClassVersion<br>xxxDescriptions | digitalSTROM system defined formats |
| Real-world identification, database matching | of the technical endpoint | hardwareGuid | hardwareModelGuid |  | schema:<id> formatted |
|  | of the hard- or software the technical endpoint device is embedded in | oemGuid | oemModelGuid |  |  |
|  | of the vendor |  | vendorId |  |  |
| End user faced info | of the device | name | model |  | free form texts, only for human readers |
|  | of the vendor |  | vendorName<br>modelVersion<br>hardwareVersion |  |  |
|  | of versions |  |  |  |  |

## Schemas used so far for Guids (schema:guid formats)

| Schema example ID | used for property | where |
|---|---|---|
| gs1: (01)4050300870342(21)3696724640 | hardwareGuid | devices which have a native GTIN and serial number, such as some DALI devices |
| gs1: (01)4050300870342 | hardwareModelGuid, oemModelGuid | devices which have a native GTIN for identifying the device model |
| gs1: gs1:(412)7640161170001 | vendorId | Vendor's GLN if vendor has one |
| uuid: 2f402f80-ea50-11e1-9b23-001778216465 | hardwareGuid | devices identified best by UUID, like hue bridge (or UPnP devices in general) |
| macaddress: 45:A2:00:BC:73:B8 | hardwareGuid | devices identified best by MAC-Adress like Smarter iKettle 2 (in general IP devices that have no better identification number of their own) |
| enoceanaddress: A4BC23D2 | hardwareGuid | EnOcean device instances (32-bit Enocean address) |
| enoceaneep: A50904 | hardwareModelGuid | EnOcean device type (24-bit profile number) |
| enoceanvendor: 002:Themokon | vendorId | EnOcean vendor Id code (and name if known by vdc) |
| hueuid: 00:17:88:01:00:bd:ef:d1-0b | hardwareGuid | hue lights |
| smartermodel: ikettle2 | hardwareModelGuid | Smarter iKettle |
| vzughomemodel: MSLQ | hardwareModelGuid | VZug Home (IP connected) devices |
| vzugeyemodel: WA-AL | hardwareModelGuid | VZug eye (optical, retrofit) devices |
| vzughome: MSLQ#7768123672 | hardwareGuid | VZug Home (IP connected) devices |
| vzugeye: WA-AL#136273722 | hardwareGuid | VZug eye (optical, retrofit) devices |
| voxnetdevicemodel: voxnet219 | hardwareModelGuid | Revox Voxnet |
| voxnetdeviceid: #R001EC0DD0B1D0 | hardwareGuid | Revox Voxnet |
| sparkcoreid: 53ff1a065067544840310697 | hardwareGuid | (experimental) particle.io based plan44 light devices |
| none |  | all *Guid | if the device does absolutely have no reliable GUID, it will not return a value |

**Figure 1: Overview of identifying properties**
