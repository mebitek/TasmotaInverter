# venus.dbus-tasmota-inverter
Service to integrate a tasmota wallplug sensor data as inverter
The script has been developed with my current RV setup in mind.

**WARNING**: I own an EDECOA 5-151B inverter, and the default settings and service behavior are specific to this particular inverter integrated into an RV.

based on the work of [Waldmensch1](https://github.com/Waldmensch1/venus.dbus-tasmota-inverter)

The Python script subscribes to a MQTT Broker and parses the typical Tasmota Sensor telegrams. These will send the values to dbus. 
The script will check High Temperature, Overload and Low voltage alarms 
The script supports changing the status of the tasmota device from GUI
The script supports **Victron Connect App VRM**:
   * visualization as Smart Phoenix Inverter 12V 1600VA 230V
   * change mode (On, Off, Eco)
   * change Low Battery Alarm
   * change Low Battery shutdown trigger

### Configuration

See config.ini and amend for your own needs.

In `[Topics]` section you can specify the L1 phase topic and the status topic. Check your tasmota device MQTT broker to get the correct ones

Example:

    `L1 = tele/tasmota_4B0B98/SENSOR`
    `CONFIG = tele/tasmota_4B0B98/STATE`
    `LWT = tele/tasmota_4B0B98/LWT`
In `[Warnings]` section you can specify the High temperature alarm limit, the overload alarm limit (10% tolerance will be added during calculation) and the Low Battery Voltage alarm limit

In `[Setup]` set `TasmotaIp` to remote control the device (On|Off) via GUI

In `[Options]` set `LowBatteryShutdown` to shut down the tasmota device when battery voltage drops under the limit



### Installation

* #### Manual
  1. Copy all the files to the /data/dbus-tasmota-inverter folder on your venus:

  2. Set permissions for files:

     `chmod 755 /data/dbus-tasmota-inverter/install.sh`

  3. run `install.sh`

  4. (optional) to uninstall just run `uninstall.sh`


* #### SetupHelper
  1. install [SetupHelper](https://github.com/kwindrem/SetupHelper)
  2. enter `Package Mager` in Settings
  3. Enter `Inactive Packages`
  4. on `new` enter the following:
     - `package name` -> `dbus-tasmota-inverter`
     - `GitHub user` -> `mebitek`
     - `GitHub branch or tag` -> `master`
  5. go to `Active packages` and click on `dbus-tasmota-inverter`
     - click on `download` -> `proceed`
     - click on `install` -> `proceed`

### Debugging
You can turn debug off on `config.ini` -> `debug=false`

The log you find in /var/log/dbus-tasmota-inverter

`tail -f -n 200 /data/log/dbus-tasmota-inverter/current.log`

You can check the status of the service with svstat:

`svstat /service/dbus-tasmota-inverter`

It will show something like this:

`/service/dbus-tasmota-inverter: up (pid 10078) 325 seconds`

If the number of seconds is always 0 or 1 or any other small number, it means that the service crashes and gets restarted all the time.

When you think that the script crashes, start it directly from the command line:

`python /data/dbus-tasmota-inverter/dbus-tasmota-inverter.py`

and see if it throws any error messages.

If the script stops with the message

`dbus.exceptions.NameExistsException: Bus name already exists: com.victronenergy.grid"`

it means that the service is still running or another service is using that bus name.

#### Restart the script

If you want to restart the script, for example after changing it, just run the following command:

`/data/dbus-tasmota-inverter/kill_me.sh`

The daemon-tools will restart the script within a few seconds.

### Hardware

Any Tasmota device, which has a Power Sensor.
Tested with NOUS A8T
