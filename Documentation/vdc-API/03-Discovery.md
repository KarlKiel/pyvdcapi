3 Discovery
==========

3.1 Requirements
----------------

- A vDC host must be discoverable by vdSMs automatically on a given network. Discovery must work without any UI on the vDC host side.
- It must be avoided that a vdSM connects to a wrong (neighbour's, for example) vDC host.

3.2 Solution
------------

- vDC hosts announce their services using Avahi (gnu implementation of Apple's Bonjour)
- vdSMs look for available vDC hosts in the Avahi announcements and connect to at least one of them. vDC hosts might reject connections if they are already connected to another vdSM.
- To avoid wrong connections, the vdSM which initiates a connection must be able to check possible vDC announcements received via Avahi against an optional whitelist. If the whitelist exists, only listed vDCs might be connected. The idea is that in small/simple installations connection is fully automatic, but if conflicts arise in large setups (like show rooms or developer environments) these can be solved by adding whitelists. Whitelists are located and maintained on the dss device.

3.3 Notes
---------

- In a future version, the dSS configurator will provide a user interface to view and edit the whitelist.
- virtual device gateways productive with dSS version 1.9 currently have a vdsm of their own in the gateway, which also announces itself via Avahi. This was required as a temporary solution, but will be phased out with the next dSS version. For new developments, running vdSM instances on devices other than a dSS is not allowed (nor needed) for production environments.
- The next planned version of the discovery mechanism will be smarter in avoiding duplicate connections and keeping existing setup stable. It will also be able to seamlessly migrate now productive virtual device gateways with a separate vdSM to using a dSS-hosted vdSM.
- vDC implementations adhering to 3.2 will continue to work as before.

3.4 Avahi service description files
-----------------------------------

- On a system with avahi-daemon installed, announcing services consists of creating .service files and putting them into /etc/avahi/services
- The service types are chosen to be very unlikely to collide with other company's services by using the "ds-" prefix. If needed, dS service names could still be registered with IANA later (see http://www.rfc-editor.org/rfc/rfc6335.txt)
- The port numbers used below are just examples, actual ports might differ.
- The advertisement for vdSMs must contain a txt record specifying the vdsm's dSUID
- Once dS services can handle ipv6, the "protocol" attribute should be set to "any"

/etc/avahi/services/ds-vdc.service

```xml
<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">digitalSTROM vDC host on %h</name>
  <service protocol="ipv4">
    <type>_ds-vdc._tcp</type>
    <port>8444</port>
  </service>
</service-group>
```

/etc/avahi/services/ds-vdsm.service

```xml
<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">digitalSTROM vdSM on %h</name>
  <service protocol="ipv4">
    <type>_ds-vdsm._tcp</type>
    <port>8441</port>
    <txt-record>dSUID=198C033E330755E78015F97AD093DD1C00</txt-record>
  </service>
</service-group>
```

