# Action Plan: Fix Remaining Compliance Gaps

**Created:** February 9, 2026  
**Target:** Complete 100% vDC API compliance  
**Effort:** Phase 1 (2h) + Phase 2 (80h) = 82 hours total

---

## Phase 1: Complete Minor Property Gaps ✅ **START HERE**

**Priority:** LOW (optional features)  
**Effort:** 2 hours  
**Impact:** 99.3% → 100% property compliance  
**Breaking Changes:** None

### Task 1.1: Implement localPriority Enforcement (1.5 hours)

**File:** [pyvdcapi/entities/vdsd.py](pyvdcapi/entities/vdsd.py)

**Changes Required:**

1. **Modify `call_scene()` method** (Line ~1550)
```python
def call_scene(
    self,
    scene: int,
    force: bool = False,
    mode: str = 'default'
) -> None:
    """
    Apply a scene to this device's output.
    
    Args:
        scene: Scene number (0-127)
        force: If True, bypass localPriority enforcement
        mode: 'default', 'min', 'max' (default applies all values)
    """
    # ✅ ADD: Check local priority enforcement
    if self._local_priority_scene and not force:
        scene_config = self._scenes.get(scene, {})
        if not scene_config.get("ignoreLocalPriority", False):
            if scene != self._local_priority_scene:
                logger.info(
                    f"Scene {scene} blocked by local priority "
                    f"(active priority: {self._local_priority_scene}). "
                    f"Use force=True to override."
                )
                return  # ✅ Block the scene call
    
    # Existing scene application logic continues below...
    scene_config = self._scenes.get(scene)
    if not scene_config:
        logger.warning(f"Scene {scene} not found")
        return
    # ... rest of existing code
```

2. **Update docstring for `set_local_priority()`** (Line ~1735)
```python
def set_local_priority(self, scene: Optional[int]) -> None:
    """
    Set local priority scene lock.
    
    When a local priority scene is set, only that scene (or scenes with
    ignoreLocalPriority=True) can be called. Other scene calls are blocked
    unless force=True is used.
    
    This is a dS 1.0 compatibility feature for local device control priority.
    
    Args:
        scene: Scene number to lock (0-127), or None to clear priority
        
    Example:
        # Lock to scene 10 (local control)
        device.set_local_priority(10)
        
        device.call_scene(5)  # Blocked (not priority scene)
        device.call_scene(10)  # Allowed (matches priority)
        device.call_scene(5, force=True)  # Allowed (force override)
        
        # Clear priority
        device.set_local_priority(None)
        device.call_scene(5)  # Now allowed
    """
    self._local_priority_scene = scene
    
    if scene is not None:
        logger.info(f"Local priority set to scene {scene}")
    else:
        logger.info("Local priority cleared")
        
    # ✅ ADD: Push property change to vdSM
    if self.output:
        self.vdc.push_property(
            dsuid=self.dsuid,
            property_path="output.state.localPriority",
            value=scene
        )
```

**Test File:** `tests/test_local_priority.py` (create new)
```python
import pytest
from pyvdcapi.entities.vdc import VdC
from pyvdcapi.constants import DSGroup, DSChannelType

def test_local_priority_blocks_other_scenes():
    """Verify localPriority blocks non-matching scenes."""
    vdc = VdC(name="Test", persistence=None)
    device = vdc.create_vdsd(
        name="Light",
        model="Dimmer",
        mac_address="00:11:22:33:44:55",
        vendor_id="test",
        primary_group=DSGroup.YELLOW
    )
    
    # Add output channel
    channel = device.add_output_channel(
        DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # Save two scenes
    channel.set_value(50.0)
    device.save_scene(5)
    
    channel.set_value(75.0)
    device.save_scene(10)
    
    # Set local priority to scene 10
    device.set_local_priority(10)
    
    # Scene 10 should work
    channel.set_value(0.0)
    device.call_scene(10)
    assert channel.get_value() == 75.0
    
    # Scene 5 should be blocked
    device.call_scene(5)
    assert channel.get_value() == 75.0  # Unchanged
    
    # Scene 5 with force should work
    device.call_scene(5, force=True)
    assert channel.get_value() == 50.0

def test_local_priority_cleared():
    """Verify clearing localPriority allows all scenes."""
    vdc = VdC(name="Test", persistence=None)
    device = vdc.create_vdsd(
        name="Light",
        model="Dimmer",
        mac_address="00:11:22:33:44:55",
        vendor_id="test",
        primary_group=DSGroup.YELLOW
    )
    
    channel = device.add_output_channel(
        DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    channel.set_value(50.0)
    device.save_scene(5)
    
    # Set and clear priority
    device.set_local_priority(10)
    device.set_local_priority(None)
    
    # Scene 5 should work now
    channel.set_value(0.0)
    device.call_scene(5)
    assert channel.get_value() == 50.0
```

**Checklist:**
- [ ] Modify `call_scene()` method
- [ ] Update `set_local_priority()` docstring
- [ ] Add property push notification
- [ ] Create test file
- [ ] Run tests: `pytest tests/test_local_priority.py -v`
- [ ] Update ARCHITECTURE.md (document priority behavior)

---

### Task 1.2: Add ignoreLocalPriority Flag (0.5 hours)

**File:** [pyvdcapi/entities/vdsd.py](pyvdcapi/entities/vdsd.py)

**Changes Required:**

1. **Update `save_scene()` method** (Line ~1630)
```python
def save_scene(
    self,
    scene: int,
    dont_care: bool = False,
    ignore_local_priority: bool = False,  # ✅ ADD parameter
    effect: int = 0
) -> None:
    """
    Save current output channel values to a scene.
    
    Args:
        scene: Scene number (0-127)
        dont_care: If True, mark scene as "don't care" (device ignores it)
        ignore_local_priority: If True, scene can bypass localPriority lock  # ✅ ADD
        effect: Transition effect (0=smooth, 1=slow, 2=custom)
    """
    if self.output is None:
        logger.warning(f"Cannot save scene {scene}: no output")
        return
        
    # Capture current channel values
    channels = {}
    for channel in self.output.channels.values():
        channels[channel.channel_type] = channel.get_value()
    
    # Store scene configuration
    scene_config = {
        "output": {
            "channels": channels
        },
        "dontCare": dont_care,
        "effect": effect,
        "ignoreLocalPriority": ignore_local_priority  # ✅ ADD
    }
    
    self._scenes[scene] = scene_config
    
    logger.info(
        f"Saved scene {scene} with {len(channels)} channels "
        f"(dontCare={dont_care}, ignorePriority={ignore_local_priority})"
    )
    
    # Persist to storage
    if self.vdc.persistence:
        self.vdc.persistence.save_device(self)
```

2. **Update property tree for scene** (Line ~900 in property tree generation)
```python
# In _get_scene_properties():
scene_properties = {
    "sceneValue": scene_config.get("output", {}).get("channels", {}),
    "dontCare": scene_config.get("dontCare", False),
    "effect": scene_config.get("effect", 0),
    "ignoreLocalPriority": scene_config.get("ignoreLocalPriority", False)  # ✅ ADD
}
```

**Test Addition:** Add to `tests/test_local_priority.py`
```python
def test_ignore_local_priority_flag():
    """Verify ignoreLocalPriority flag bypasses priority lock."""
    vdc = VdC(name="Test", persistence=None)
    device = vdc.create_vdsd(
        name="Light",
        model="Dimmer",
        mac_address="00:11:22:33:44:55",
        vendor_id="test",
        primary_group=DSGroup.YELLOW
    )
    
    channel = device.add_output_channel(
        DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # Save scene 5 with ignoreLocalPriority=True
    channel.set_value(50.0)
    device.save_scene(5, ignore_local_priority=True)
    
    # Save scene 10 normally
    channel.set_value(75.0)
    device.save_scene(10, ignore_local_priority=False)
    
    # Set local priority to scene 10
    device.set_local_priority(10)
    
    # Scene 5 should work (ignoreLocalPriority=True)
    channel.set_value(0.0)
    device.call_scene(5)
    assert channel.get_value() == 50.0
    
    # Scene 10 should also work (matches priority)
    device.call_scene(10)
    assert channel.get_value() == 75.0
```

**Checklist:**
- [ ] Add `ignore_local_priority` parameter to `save_scene()`
- [ ] Store flag in scene config
- [ ] Add to property tree
- [ ] Add test case
- [ ] Run tests: `pytest tests/test_local_priority.py::test_ignore_local_priority_flag -v`
- [ ] Update API_REFERENCE.md (document flag)

---

## Phase 2: Fix Architectural Issues ⚠️ **BREAKING CHANGES**

**Priority:** HIGH (critical compliance)  
**Effort:** 80 hours  
**Impact:** 60% → 100% architectural compliance  
**Breaking Changes:** YES (requires v2.0)

### Task 2.1: Device Immutability After Announcement (16 hours)

See **VDC_API_COMPLIANCE_ANALYSIS.md Issue #1** for full details.

**Summary:**
1. Add `_announced` flag to VdSD
2. Add `mark_announced()` method (called by vDC after announcedevice)
3. Block all feature addition methods when `_announced=True`
4. Raise helpful error with vanish/recreate instructions
5. Update all examples to create full device BEFORE announcement
6. Add tests for immutability enforcement

**Files to Modify:**
- `pyvdcapi/entities/vdsd.py` (add flag, modify 4 methods)
- `pyvdcapi/entities/vdc.py` (call mark_announced())
- `examples/*.py` (ensure features added before announcement)
- `tests/test_immutability.py` (create new)
- `API_REFERENCE.md` (document pattern)

---

### Task 2.2: Button ClickType Refactoring (24 hours)

See **VDC_API_COMPLIANCE_ANALYSIS.md Issue #2** for full details.

**Summary:**
1. Create new `ButtonInput` class (API-compliant core)
2. Add `set_click_type(click_type)` method (direct input)
3. Support all 15 clickType values (0-14, 255)
4. Move timing logic to separate `DSButtonStateMachine` template
5. Deprecate old `Button` class
6. Update all examples
7. Add tests for all clickTypes

**Files to Create:**
- `pyvdcapi/components/button_input.py` (API-compliant core)
- `pyvdcapi/components/button_templates.py` (optional state machine)

**Files to Modify:**
- `pyvdcapi/entities/vdsd.py` (add_button, add_ds_button methods)
- `examples/*.py` (use new ButtonInput)
- `tests/test_button_clicktypes.py` (create new)

---

### Task 2.3: Single Output Per Device (40 hours)

See **VDC_API_COMPLIANCE_ANALYSIS.md Issue #3** for full details.

**Summary:**
1. Change `_outputs: Dict[int, Output]` to `_output: Optional[Output]`
2. Remove `output_id` parameter everywhere
3. Update `add_output_channel()` to create output on first call
4. Update property tree generation (no outputID)
5. Update YAML persistence format
6. Create migration tool for existing configs
7. Update all examples
8. Comprehensive testing

**Files to Modify:**
- `pyvdcapi/entities/vdsd.py` (major refactor)
- `pyvdcapi/components/output.py` (remove output_id)
- `pyvdcapi/persistence/*.py` (YAML format change)
- `tools/migrate_v1_to_v2.py` (create migration tool)
- `examples/*.py` (update all)
- `tests/test_single_output.py` (create new)

---

## Success Criteria

### Phase 1 Complete When:
- [ ] localPriority enforcement working
- [ ] ignoreLocalPriority flag implemented
- [ ] 3 new tests passing
- [ ] Documentation updated
- [ ] Property compliance: 150/150 (100%)

### Phase 2 Complete When:
- [ ] All 3 architectural issues fixed
- [ ] Migration guide published
- [ ] All examples updated
- [ ] All tests passing (60+ tests)
- [ ] v2.0 released
- [ ] Architectural compliance: 100%

---

## Testing Strategy

### Unit Tests (Phase 1)
```bash
# Test local priority
pytest tests/test_local_priority.py -v

# Verify no regressions
pytest tests/ -v
```

### Integration Tests (Phase 2)
```bash
# Test immutability
pytest tests/test_immutability.py -v

# Test new button API
pytest tests/test_button_clicktypes.py -v

# Test single output
pytest tests/test_single_output.py -v

# Test migration tool
pytest tests/test_v1_to_v2_migration.py -v

# Run full suite
pytest tests/ -v --cov=pyvdcapi
```

---

## Documentation Updates

### Phase 1
- [ ] Update API_REFERENCE.md (localPriority section)
- [ ] Update ARCHITECTURE.md (scene priority behavior)
- [ ] Update COMPREHENSIVE_API_COMPLIANCE_REPORT.md (mark gaps as fixed)
- [ ] Add inline docstrings for new parameters

### Phase 2
- [ ] Create MIGRATION_GUIDE_V1_TO_V2.md
- [ ] Update README.md (breaking changes notice)
- [ ] Update API_REFERENCE.md (all 3 architectural changes)
- [ ] Update ARCHITECTURE.md (new data model)
- [ ] Create CHANGELOG.md (v2.0 entry)
- [ ] Update VDC_API_COMPLIANCE_ANALYSIS.md (mark issues as fixed)
- [ ] Add compliance badges to README

---

## Release Planning

### Version 1.1 (Phase 1 Complete)
- Minor version bump (no breaking changes)
- Complete property compliance
- All optional features working
- Release notes: "100% property compliance achieved"

### Version 2.0 (Phase 2 Complete)
- Major version bump (breaking changes)
- Full architectural compliance
- Migration guide included
- Release notes: "Full vDC API v2.0+ compliance"

---

## Time Estimates

| Task | Effort | Notes |
|------|--------|-------|
| **Phase 1 Total** | **2 hours** | Non-breaking |
| localPriority enforcement | 1.5h | Code + tests |
| ignoreLocalPriority flag | 0.5h | Code + tests |
| **Phase 2 Total** | **80 hours** | Breaking changes |
| Device immutability | 16h | Week 1 |
| Button refactoring | 24h | Week 2 |
| Single output enforcement | 40h | Weeks 3-4 |
| **Grand Total** | **82 hours** | ~2.5 weeks full-time |

---

## Risk Assessment

### Phase 1 Risks: LOW ✅
- Minimal code changes
- No breaking changes
- Feature is optional/deprecated
- Easy to revert if issues

### Phase 2 Risks: MEDIUM ⚠️
- Breaking API changes
- User migration required
- Config format changes
- Extensive testing needed

**Mitigation:**
1. Comprehensive test suite before release
2. Detailed migration guide
3. Deprecation warnings in v1.x
4. Beta release cycle for v2.0

---

## Next Steps

**Immediate (Today):**
1. Start Phase 1, Task 1.1
2. Implement localPriority enforcement
3. Run tests

**This Week:**
1. Complete Phase 1 (all 2 hours)
2. Release v1.1
3. Plan Phase 2 sprint schedule

**This Month:**
1. Execute Phase 2 (80 hours over 2-3 weeks)
2. Beta test v2.0
3. Release v2.0 with migration guide

---

**Document Version:** 1.0  
**Last Updated:** February 9, 2026  
**Status:** Ready to execute
