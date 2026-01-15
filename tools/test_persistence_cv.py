import sys
import os
import pprint

# Ensure project root is on sys.path so package imports work when running scripts
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pyvdcapi.persistence.yaml_store import YAMLPersistence

yaml_path = os.path.join(os.path.dirname(__file__), '..', 'example_announced_config.yaml')
yaml_path = os.path.abspath(yaml_path)
print('Using YAML:', yaml_path)

p = YAMLPersistence(yaml_path, auto_save=True)

dsuid = '000000027F9202F411B8B5822402000000'
bracket_dsuid = str([dsuid])

print('\nBefore updates:')
print('get_vdsd(dsuid)=')
pprint.pprint(p.get_vdsd(dsuid))
print("get_vdsd(bracket_dsuid)=")
pprint.pprint(p.get_vdsd(bracket_dsuid))

print('\nUpdating canonical dsuid controlValues.TemperatureZone -> 22.0')
p.update_vdsd_property(dsuid, 'controlValues.TemperatureZone', 22.0)

print('Updating bracket_dsuid controlValues.TemperatureZone -> 23.0')
try:
    p.update_vdsd_property(bracket_dsuid, 'controlValues.TemperatureZone', 23.0)
except Exception as e:
    print('Exception when updating bracket_dsuid:', e)

print('\nAfter updates:')
print('get_vdsd(dsuid)=')
pprint.pprint(p.get_vdsd(dsuid))
print('get_vdsd(bracket_dsuid)=')
pprint.pprint(p.get_vdsd(bracket_dsuid))

print('\nDone')
