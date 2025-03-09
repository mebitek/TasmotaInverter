#!/bin/bash

if [[ -L /service/dbus-tasmota-inverter ]]; then
  rm /service/dbus-tasmota-inverter
fi

if [[ -L /opt/victronenergy/service/dbus-tasmota-inverter ]]; then
  rm /opt/victronenergy/service/dbus-tasmota-inverter
fi

./kill_me.sh

