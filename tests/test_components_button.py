import time
from pyvdcapi.components.button_input import ButtonInput, ClickType


def test_button_input_to_from_dict():
    """Test ButtonInput serialization and deserialization."""
    class DummyVdSD:
        def push_button_state(self, button_id, click_type):
            pass

    vdsd = DummyVdSD()
    btn = ButtonInput(vdsd=vdsd, name="TestBtn", button_type=1, button_id=1)

    # initial to_dict shape
    d = btn.to_dict()
    assert d["description"]["name"] == "TestBtn"
    assert d["description"]["buttonID"] == 1
    assert d["description"]["buttonType"] == 1
    assert "settings" in d
    assert "state" in d

    # Check initial state
    assert d["state"]["clickType"] == ClickType.IDLE
    assert d["state"]["value"] is None

    # Update from dict (settings + state)
    new = {
        "description": {"name": "Renamed"},
        "settings": {"group": 5, "function": 3},
        "state": {"value": True, "clickType": 0}
    }
    btn.from_dict(new)
    assert btn.name == "Renamed"
    assert btn._value is True
    assert btn._click_type == 0


def test_button_input_click_type_setting():
    """Test setting clickType values."""
    class DummyVdSD:
        def __init__(self):
            self.pushed_states = []
            
        def push_button_state(self, button_id, click_type):
            self.pushed_states.append((button_id, click_type))

    vdsd = DummyVdSD()
    btn = ButtonInput(vdsd=vdsd, name="TestBtn", button_type=1, button_id=5)

    # Test valid clickType values
    btn.set_click_type(0)  # tip_1x
    assert btn.get_click_type() == 0
    assert len(vdsd.pushed_states) == 1
    assert vdsd.pushed_states[0] == (5, 0)

    btn.set_click_type(4)  # hold_start
    assert btn.get_click_type() == 4
    assert len(vdsd.pushed_states) == 2

    btn.set_click_type(255)  # idle
    assert btn.get_click_type() == 255
    assert len(vdsd.pushed_states) == 3

    # Test invalid clickType
    try:
        btn.set_click_type(99)  # Invalid
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid clickType" in str(e)


def test_button_input_click_type_constants():
    """Test ClickType constants and names."""
    assert ClickType.TIP_1X == 0
    assert ClickType.TIP_2X == 1
    assert ClickType.HOLD_START == 4
    assert ClickType.HOLD_END == 6
    assert ClickType.LOCAL_OFF == 11
    assert ClickType.IDLE == 255

    assert ClickType.name(0) == "tip_1x"
    assert ClickType.name(4) == "hold_start"
    assert ClickType.name(255) == "idle"


def test_button_input_state_value():
    """Test button value (active/inactive state)."""
    class DummyVdSD:
        def push_button_state(self, button_id, click_type):
            pass

    vdsd = DummyVdSD()
    btn = ButtonInput(vdsd=vdsd, name="TestBtn", button_type=1)

    # Initial state
    assert btn.get_value() is None

    # Set active
    btn.set_value(True)
    assert btn.get_value() is True

    # Set inactive
    btn.set_value(False)
    assert btn.get_value() is False

    # Set unknown
    btn.set_value(None)
    assert btn.get_value() is None


def test_button_input_get_description():
    """Test button description properties."""
    class DummyVdSD:
        def push_button_state(self, button_id, click_type):
            pass

    vdsd = DummyVdSD()
    btn = ButtonInput(
        vdsd=vdsd,
        name="Nav Up",
        button_type=4,  # 4-way with center
        button_id=10,
        button_element_id=2  # Up
    )

    desc = btn.get_description()
    assert desc["name"] == "Nav Up"
    assert desc["buttonID"] == 10
    assert desc["buttonType"] == 4
    assert desc["buttonElementID"] == 2
    assert desc["supportsLocalKeyMode"] is True


def test_button_input_get_settings():
    """Test button settings properties."""
    class DummyVdSD:
        def push_button_state(self, button_id, click_type):
            pass

    vdsd = DummyVdSD()
    btn = ButtonInput(
        vdsd=vdsd,
        name="TestBtn",
        button_type=1,
        group=2,
        function=5,
        mode=2,
        channel=1,
        setsLocalPriority=True,
        callsPresent=True
    )

    settings = btn.get_settings()
    assert settings["group"] == 2
    assert settings["function"] == 5
    assert settings["mode"] == 2
    assert settings["channel"] == 1
    assert settings["setsLocalPriority"] is True
    assert settings["callsPresent"] is True


def test_button_input_update_settings():
    """Test updating button settings."""
    class DummyVdSD:
        def push_button_state(self, button_id, click_type):
            pass

    vdsd = DummyVdSD()
    btn = ButtonInput(vdsd=vdsd, name="TestBtn", button_type=1)

    # Update settings
    btn.update_settings({
        "group": 3,
        "function": 7,
        "mode": 5
    })

    settings = btn.get_settings()
    assert settings["group"] == 3
    assert settings["function"] == 7
    assert settings["mode"] == 5

