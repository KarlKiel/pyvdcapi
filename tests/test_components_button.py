import time
from pyvdcapi.components.button import Button


def test_button_to_from_dict_and_events():
    class DummyVdSD:
        pass

    vdsd = DummyVdSD()
    btn = Button(vdsd=vdsd, name="TestBtn", button_type=0, button_id=1)

    # initial to_dict shape
    d = btn.to_dict()
    assert d["name"] == "TestBtn"
    assert d["buttonID"] == 1
    assert "settings" in d
    assert "state" in d

    # subscribe to events
    events = []

    def cb(button_id, event_type):
        events.append((button_id, event_type))

    btn.on_press(cb)

    # simulate click
    btn.click()
    time.sleep(0.01)
    assert len(events) >= 1

    # update from dict (settings + state)
    new = {"name": "Renamed", "settings": {"group": 5, "function": 3}, "state": {"value": True}}
    btn.from_dict(new)
    assert btn.name == "Renamed"
    assert btn._pressed is True
