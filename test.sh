#!/bin/sh
rm ui/tests/*.pyc || true
rm -rf ui/tests/__pycache__/ || true
python -B -m pytest --doctest-modules -v --doctest-ignore-import-errors --ignore=output/drivers --ignore=input/drivers --ignore=apps/hardware_apps/ --ignore=apps/example_apps/fire_detector --ignore=apps/test_hardware
