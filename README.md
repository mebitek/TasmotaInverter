# venus.TasmotaInverter v0.4.5
Service to integrate a tasmota wallplug sensor data as inverter.

The script has been developed with my current RV setup in mind.

**WARNING**: I own an EDECOA 5-151B inverter, and the default settings and service behavior are specific to this particular inverter integrated into an RV.

based on the work of [Waldmensch1](https://github.com/Waldmensch1/venus.dbus-tasmota-inverter)

### Refrences
* [VE.Direct-HEX-Protocol-Phoenix-Inverter](https://www.victronenergy.com/upload/documents/VE.Direct-HEX-Protocol-Phoenix-Inverter.pdf)
* [Venus Wiki](https://github.com/victronenergy/venus/wiki/dbus#inverter)
* [Reg Info](https://communityarchive.victronenergy.com/storage/attachments/reg-info.pdf)

The Python script subscribes to a MQTT Broker and parses the typical Tasmota Sensor telegrams. These will send the values to dbus. 

The script will check High Temperature, Overload and Low voltage alarms 

The script supports changing the status of the tasmota device from GUI

The script supports **Victron Connect App VRM**:
   * visualization as Smart Phoenix Inverter 12V 2000VA 230V
   * change mode (On, Off, Eco)
   * change Low Battery Alarm
   * change Low Battery shutdown trigger

### Configuration

You need to configure you Tasmota MQQT to point to Venus OS MQTT broker

* #### GUI
    You can configure directly from gui-v1 interface `Settings` -> `Tasmota Inverter`

* #### Manual
    See config.sample.ini and amend for your own needs. Copy to `/data/conf` as `tasmota.config.ini`
    - In `[Setup]` set `TasmotaIp` to remote control the device (On|Off) via GUI
    - In `MQTTBroker` configure your MQQT broker, default is the Venus OS MQTT broker (127.0.0.1)
    - In `[Topics]` section you can specify the L1 phase topic, the status topic and the state topic. Check your tasmota device MQTT broker to get the correct ones
    
      Example:

          `L1 = tele/tasmota_4B0B98/SENSOR`
          `CONFIG = tele/tasmota_4B0B98/STATE`
          `LWT = tele/tasmota_4B0B98/LWT`

    - In `[Warnings]` section you can specify the High temperature alarm limit, the overload alarm limit (10% tolerance will be added during calculation) and the Low Battery Voltage alarm limit. All this settings will raise a warning notification
    - In `[Options]` set `LowBatteryShutdown` to shut down the tasmota device when battery voltage drops under the limit and `ChargeDetected` as Tasmnota will not power on after a low battery shutdown event until the charge detected value has not been reached



### Installation

* #### SetupHelper
  1. install [SetupHelper](https://github.com/kwindrem/SetupHelper)
  2. enter `Package Mager` in Settings
  3. Enter `Inactive Packages`
  4. on `new` enter the following:
     - `package name` -> `TasmotaInverter`
     - `GitHub user` -> `mebitek`
     - `GitHub branch or tag` -> `master` 
  5. go to `Active packages` and click on `TasmotaInverter`
     - click on `download` -> `proceed`
     - click on `install` -> `proceed`

| velib_pyhton available [here](https://github.com/victronenergy/velib_python/tree/master) 

### Debugging
You can turn debug off on `config.ini` -> `debug=false`

The log you find in /var/log/TasmotaInverter

`tail -f -n 200 /data/log/TasmotaInverter/current`

You can check the status of the service with svstat:

`svstat /service/TasmotaInverter`

It will show something like this:

`/service/TasmotaInverter: up (pid 10078) 325 seconds`

If the number of seconds is always 0 or 1 or any other small number, it means that the service crashes and gets restarted all the time.

When you think that the script crashes, start it directly from the command line:

`python /data/TasmotaInverter/TasmotaInverter.py`

and see if it throws any error messages.

If the script stops with the message

`dbus.exceptions.NameExistsException: Bus name already exists: com.victronenergy.grid"`

it means that the service is still running or another service is using that bus name.


### Hardware

Any Tasmota device, which has a Power Sensor.
Tested with NOUS A8T
