from adbutils import adb
from msc.adbcap import ADBCap
from msc.adbblitz import ADBBlitz
from msc.minicap import MiniCap
from msc.droidcast import DroidCast

ADBCap(adb.device_list()[0].serial).save_screencap("adb.png")
ADBBlitz(adb.device_list()[0].serial).save_screencap("adbblitz.png")
MiniCap(adb.device_list()[0].serial).save_screencap("minicap.png")
DroidCast(adb.device_list()[0].serial).save_screencap("droidcast.png")
