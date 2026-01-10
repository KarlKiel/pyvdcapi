# 5 digitalSTROM mapping compatibility

An important design goal for the vDC API and the property set was to avoid carrying over dS specific limitations. On the other hand, the vDC API was designed to support capabilities current dSS 1.x architecture can't support yet, but are likely to be implemented in future dS versions. Still, the vDC + vdSM needs to be compatible with existing dSS 1.x installations.

To achieve this, vDC devices (vdSDs) that provide functionality similar or equal to existing digitalSTROM hardware devices (dSDs), must have sensible default settings that make them mappable into existing dSS 1.x installations. This chapter lists the conventions that must be followed for certain device types to make them mappable into dSS 1.x environments.

## 5.1 2-way buttons

2-way buttons (rockers) like present in many EnOcean devices must conform to the following default behaviour:

- The vdSD must have two button inputs (represented by 2 array elements in the buttonInputDescriptions/Settings/States property arrays)
- The buttonInput with index = 0 must represent the "down" button
- The buttonInput with index = 1 must represent the "up" button
- buttonInputSettings[0].mode must be 6 (down button paired with second input)
- buttonInputSettings[1].mode must be 9 (up button paired with first input)

## 5.2 Multiple vdSDs in a single hardware device

Some hardware devices contain more than one instance of a certain functional unit. Usually, these are represented as a separate vdSD each, to allow maximum flexibility in the way the functional units can be used.

For example, a dual 2-way button EnOcean device will be represented as 2 entirely separate vdSDs, because despite the physical proximity, each button might control a different zone, group or function.

By default, such a device will be represented as 2 separate SW-TKM210 (dual input) devices. However, the vdSM might want to represent it as a single SW-TKM200 (quad input) device. To allow the vdSM to find out which and how many vdSDs are in the same hardware device, the vdSD should expose this information as follows:

- The dSUID has a 17th byte reserved to enumerate devices belonging to the same hardware, starting at zero.
- The first 16 bytes of the dSUID needs to be the same for all vdSD belonging to the same hardware.
- Usually, multiple devices are enumerated 0,1,2, etc. However, in some cases, a hardware device might have different configurations with different numbers of vdSD depending on configuration - in these cases enumeration might follow other schemes than simple increment. For example, the aforementioned dual 2-way button EnOcean device uses 0 for the first and 2 for the second rocker - to possibly allow representing each rocker as two separate vdSDs (0,1 and 2,3).
- This association of vdSDs to a containing hardware device must only be made when the number of contained vdSDs and their enumeration is unambiguous and permanent. So just 3 modules that usually ship mounted on a common frame, but can be easily separated and used independently should not use the enumeration but have fully distinct dSUIDs (different in first 16 bytes).
