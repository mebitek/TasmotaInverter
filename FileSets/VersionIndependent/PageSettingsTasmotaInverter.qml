/////// new menu for system shutdown

import QtQuick 1.1
import "utils.js" as Utils
import com.victron.velib 1.0

MbPage
{
	id: root
	title: qsTr("Tasmota Inverter")

    model: VisibleItemModel
    {
        MbItemText
        {
            text: qsTr("Tasmota Inverter not running")
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignLeft
            show: !tasmotaItem.valid
        }

        MbItemText
        {
            id: tasmota-ip
            name: qsTr("TasmotaIp")
            bind: Utils.path("com.victronenergy.settings", "/Settings/Tasmota/Setup/TasmotaIp")
            writeAccessLevel: User.AccessInstaller
        }
    }
}