/////// new menu for system shutdown

import QtQuick 1.1
import "utils.js" as Utils
import com.victron.velib 1.0

MbPage
{
	id: root
	title: qsTr("Tasmota Inverter")
    VBusItem { id: tasmotaItem; bind: Utils.path("com.victronenergy.inverter.tasmota", "/Connected") }

    property VBusItem ipAddressesItem: VBusItem { bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Setup/TasmotaIp" }
    model: Utils.stringToIpArray(ipAddressesItem.value)

    model: VisibleItemModel
    {
        // Setup
        MbItemText
        {
            text: qsTr("Tasmota Inverter not running")
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignLeft
            show: !tasmotaItem.valid
        }

        MbEditBox {
            description: "Inverter Name"
            maximumLength: 20
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Setup/Name"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Serial"
            maximumLength: 20
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Setup/Serial"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBoxIp {
            description: "Tasmota IP"
            item.value: model
            show: tasmotaItem.valid
        }

        // Broker

        MbEditBox {
            description: "MQTT Broker Name"
            maximumLength: 20
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/MQTTBroker/Name"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBoxIp {
            description: "MQTT Broker Address"
            item.value: "192.168.003.012"
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "MQTT Broker Port"
            maximumLength: 6
            numericOnlyLayout: true
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/MQTTBroker/Port"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Topic L1"
            maximumLength: 50
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Topics/L1"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Topic CONFIG"
            maximumLength: 50
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Topics/CONFIG"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Topic LWT"
            maximumLength: 50
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Topics/LWT"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        // Options

        MbEditBox {
            description: "High Temp Warning"
            maximumLength: 3
            numericOnlyLayout: true
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Warnings/HighTemperature"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Overload Warning"
            maximumLength: 5
            numericOnlyLayout: true
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Warnings/Overload"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Low Voltage Warning"
            maximumLength: 5
            matchString: "0123456789."
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Warnings/LowVoltage"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Low Battery Shutdown"
            maximumLength: 5
            matchString: "0123456789."
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Options/LowBatteryShutdown"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

        MbEditBox {
            description: "Charge Detected"
            maximumLength: 5
            matchString: "0123456789."
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/Options/ChargeDetected"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }


    }
}