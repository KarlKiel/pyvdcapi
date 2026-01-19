from pyvdcapi.components.sensor import Sensor


def test_sensor_update_and_hysteresis():
    s = Sensor(
        vdsd=None,
        name="Temp",
        sensor_type="temperature",
        unit="C",
        sensor_id=1,
        min_value=-40.0,
        max_value=125.0,
        resolution=0.1,
        initial_value=20.0,
    )

    calls = []

    def cb(sensor_id, value):
        calls.append((sensor_id, value))

    s.on_change(cb, hysteresis=0.5)
    # small change below hysteresis -> no callback
    s.update_value(20.2)
    assert len(calls) == 0

    # larger change -> callback
    s.update_value(21.0)
    assert len(calls) == 1

    # out-of-range rejected
    s.update_value(200.0)
    assert s.has_error() is True
