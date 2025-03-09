#!/bin/bash

if [[ -L /service/dbus-tasmota-inverter ]]; then
  echo "Service /service already exists"
else
  ln -s /data/dbus-tasmota-inverter/service /service/dbus-tasmota-inverter
fi

if [[ -L /opt/victronenergy/service/dbus-tasmota-inverter ]]; then
  echo "Service /opt/victronenergy/service/ already exists"
else
  ln -s  /data/dbus-tasmota-inverter/service /opt/victronenergy/service/dbus-tasmota-inverter
fi

chmod 755 /data/dbus-tasmota-inverter/dbus-tasmota-inverter.py
chmod 755 /data/dbus-tasmota-inverter/uninstall.sh