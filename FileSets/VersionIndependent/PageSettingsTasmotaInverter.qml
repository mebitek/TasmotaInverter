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
            id: tasmotaIp
            name: qsTr("TasmotaIp")
            bind: Utils.path("com.victronenergy.settings", "/Settings/Tasmota/Setup/TasmotaIp")
            writeAccessLevel: User.AccessInstaller
        }
    }
}