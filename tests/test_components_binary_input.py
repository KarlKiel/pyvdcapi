from pyvdcapi.components.binary_input import BinaryInput


def test_binary_input_state_and_callbacks():
    class DummyVdSD:
        pass

    vdsd = DummyVdSD()
    bi = BinaryInput(vdsd=vdsd, name="Door", input_type="contact", input_id=2, invert=False, initial_state=False)

    events = []

    def on_change(input_id, state):
        events.append((input_id, state))

    bi.on_change(on_change)

    # change state
    bi.set_state(True)
    assert bi.get_state() is True
    assert len(events) == 1

    # to_dict contains nested state
    d = bi.to_dict()
    assert d["name"] == "Door"
    assert "state" in d and d["state"]["value"] is True
