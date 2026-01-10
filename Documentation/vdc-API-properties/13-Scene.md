## 4.10 Scene

- A scene stores a set of values to apply to the outputs of the device when a particular scene is called.
- As outputs can be looked at in two different ways, by index or by channel (see description for 4.1.3 "Outputs" above), each scene contains the scene values for each output in two forms, once by output number (property "outputs") and once by channel type (property "channels")

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| channels | r/w | list of property elements | For each channel, a scene value (consisting of value and dontCare flag, see 4.10.1 Scene Value below).<br>• represented as a list of property elements, one for each channel in the device.<br>• The property elements are named by channel type id (which can be 0 for devices controlling an unspecified functionality, such as a generic switch output) |
| effect | r/w | integer enum | Specifies the effect to be applied when this scene is invoked. The following standard effects are defined (%%% note: enum might change, specification in discussion %%%):<br><br>0 : no effect, immediate transition<br>1 : smooth normal transition (corresponds with former dimTimeSelector==0)<br>2 : slow transition (corresponds with former dimTimeSelector==1)<br>3 : very slow transition (corresponds with former dimTimeSelector==2)<br>4 : blink (for light devices) / alerting (in general: an effect that draws the user's attention)<br><br>Notes:<br>• stored scene values may or may not be used to parametrize the effect, depending on the type of effect. For example, the blink effect with a multi-color lamp must use the color values as set in the scene, regardless of the dontCare flags.<br>• When the effect has finished, channels with dontCare set will revert to the value present before the effect, while channels with dontCare not set are expected to have now the values as stored in the scene. |
| dontCare | r/w | boolean | scene-global dontCare flag: if set, calling this scene does not apply any of the stored channel values, regardless of the individual scene value's dontCare flags |
| ignoreLocalPriority | r/w | boolean | calling this scene overrides local priority |

### 4.10.1 Scene Value

- A scene value contains the value to apply to the related output when the scene is called, and the dontCare flag that can be set to prevent the value to be applied

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| value | r/w | double | The value for the related channel. The value range and resolution is the same as for the related channel's channelState value property |
| dontCare | r/w | boolean | channel-specific dontCare flag: if set, calling this scene does not apply the stored channel value (but possibly other channel's values which don't have dontCare set) |
| automatic | r/w | boolean | channel-specific automatic flag: if set, calling this scene activates the internal automatic control logic |
