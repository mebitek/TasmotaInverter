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
        
    }
}