/////// new menu for system shutdown

import QtQuick 1.1
import "utils.js" as Utils
import com.victron.velib 1.0

MbPage
{
	id: root
	title: qsTr("Tasmota Inverter")
    VBusItem { id: tasmotaItem; bind: Utils.path("com.victronenergy.inverter.tasmota", "/Connected") }

    model: VisibleItemModel
    {
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
            item.value: "192.168.003.012"
        }

        MbEditBox {
            description: "MQTT Broker Name"
            maximumLength: 20
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/MQTTBroker/Name"
            writeAccessLevel: User.AccessUser
        }

        MbEditBoxIp {
            description: "MQTT Broker Address"
            item.value: "192.168.003.012"
        }

        MbEditBox {
            description: "MQTT Broker Port"
            maximumLength: 6
            numericOnlyLayout: true
            item.bind: "com.victronenergy.inverter.tasmota/Settings/Tasmota/MQTTBroker/Port"
            writeAccessLevel: User.AccessUser
            show: tasmotaItem.valid
        }

    }
}