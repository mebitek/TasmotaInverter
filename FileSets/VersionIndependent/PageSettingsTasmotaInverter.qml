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
        }

        MbEditBoxIp {
            description: "Tasmota IP"
            item.value: "192.168.003.012"
        }

        MbEditBoxIp {
            description: "Broker Address"
            item.value: "192.168.003.012"
        }
    }
}