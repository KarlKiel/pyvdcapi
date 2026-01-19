from pyvdcapi.components.output_channel import OutputChannel


def test_output_channel_set_and_from_dict():
    # use simple int for channel_type
    ch = OutputChannel(
        vdsd=None, channel_type=1, min_value=0.0, max_value=100.0, resolution=0.5, initial_value=0.0, name="Bright"
    )

    # set value and check rounding to resolution
    ch.set_value(33.3)
    assert abs(ch.get_value() - 33.5) < 1e-6

    # to_dict contains expected keys
    d = ch.to_dict()
    assert d["channelType"] == 1
    assert "value" in d

    # from_dict via flat value
    ch.from_dict({"value": 50})
    assert ch.get_value() == 50

    # from nested state
    ch.from_dict({"state": {"value": 20}})
    assert ch.get_value() == 20
