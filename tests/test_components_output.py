from pyvdcapi.components.output import Output
from pyvdcapi.components.output_channel import OutputChannel


def test_output_channels_list_and_notify():
    class DummyVdSD:
        def __init__(self):
            self.events = []

        def _on_output_change(self, output_id, channel_type, value):
            self.events.append((output_id, channel_type, value))

    vdsd = DummyVdSD()
    out = Output(vdsd=vdsd, output_id=0, output_function="dimmer", output_mode="gradual", push_changes=True)

    ch = OutputChannel(
        vdsd=vdsd, channel_type=1, min_value=0.0, max_value=100.0, resolution=1.0, initial_value=0.0, name="B"
    )
    out.add_channel(ch)

    # to_dict should export channels as list
    d = out.to_dict()
    assert isinstance(d.get("channels"), list)

    # set value should notify vdsd via _on_output_change
    out.set_channel_value(1, 42.0)
    assert vdsd.events and vdsd.events[-1][2] == 42.0

    # from_dict accepts list entries and creates missing channels
    out2 = Output(vdsd=vdsd, output_id=1)
    out2.from_dict({"channels": [{"channelType": 5, "min": 0.0, "max": 10.0, "name": "C"}]})
    # new channel added
    assert any(ch for ch in out2.channels.values() if ch.name == "C")
