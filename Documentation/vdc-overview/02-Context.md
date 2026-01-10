# 2 Context

digitalSTROM virtual device containers (vDC) enable the integration of IP based devices into the digitalSTROM System similar to adding digitalSTROM terminal blocks (dSD) to the system. IP based devices in the local network run a vDC to connect to the digitalSTROM System thru a virtual digitalSTROM Meter (vdSM). A vDC can host multiple devices or device classes. A vDC is even suitable to integrate a gateway to another bus- or network-technology e.g. enocean, dali asf.

3 different device types can be distinguished.

**Figure 1: digitalSTROM vDC overview**

## 2.1 device types

- device type 1 integrates devices thru the vDSM and the vDC running on the digitalSTROM Server module of the digitalSTROM installation.
- device type 2 integrates devices thru the vdSM running on the digitalSTROM Server module of the digitalSTROM installation. The vDC component is running on the physical device.
- device type 3 serves as a gateway to integrate multiple devices using bus- or network-technologies like IP, Enocean, Zigbee, EEBUS etc.

Please get in touch with the digitalSTROM AG to define which device type is suitable for your product.

## 2.2 device detail

The effort to integrate devices is reduced to program the glue logic to connect the vDC API to the real devices API. Currently there are two open source projects, libdsvdc and vdcd, both abstracting the vDC API and offering a set of basic functionality which greatly reduces the effort to integrate devices. Depending on the type of device(s) to integrate, one or the other project might be more helpful.

- libdsvdc is a lightweight C library, targeted at device vdcs (device type 1+2)
- vdcd is a C++ framework designed primarily for gateway devices (device type 3) integrating entire device classes with standard dS behaviour.

**Figure 2: device detail**

## 2.3 physical device OS

vDC is available for embedded linux. Running a vDC using another physical device OS is possible.

## 2.4 digitalSTROM configuration UI device representation

vDC's are displayed in the UI together with dSM devices. A vDC has a (virtual) standard room where all connected vdSD's are shown initially. vdSD's can be assigned to real rooms and behave exactly like real digitalSTROM Terminal blocks.

## 2.5 Discovery

vDC hosts announce their services using Avahi (gnu implementation of Apple's Bonjour)

vdSMs look for available vDC hosts in the Avahi announcements and connect to at least one of them.

vDC hosts might reject connections if they are already connected to another vdSM.

To avoid wrong connections, the vdSM which initiates a connection must be able to check possible vDC announcements received via Avahi against an optional whitelist. If the whitelist exists, only listed vDCs might be connected. The idea is that in small/simple installations connection is fully automatic, but if conflicts arise in large setups (like show rooms or developer environments) these can be solved by adding whitelists. Whitelists are located and maintained on the dss device.
