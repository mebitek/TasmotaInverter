#!/bin/bash
wget -q https://raw.githubusercontent.com/victronenergy/velib_python/refs/heads/master/ve_utils.py -O ve_utils.py
wget -q https://raw.githubusercontent.com/victronenergy/velib_python/refs/heads/master/vedbus.py -O vedbus.py

chmod 755 /data/dbus-tasmota-inverter/dbus-tasmota-inverter.py
chmod 755 /data/dbus-tasmota-inverter/service/run
chmod 755 /data/dbus-tasmota-inverter/kill_me.sh
chmod 755 /data/dbus-tasmota-inverter/uninstall.sh