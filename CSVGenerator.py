import struct
import zlib

config = {
    "VersionMajor": 0,
    "VersionMinor": 0,
    "VersionPatch": 1,
    "HeaterRatedPower": 1700,
    "Heater1Wattage": 600,
    "Heater2Wattage": 500,
    "Heater3Wattage": 600,
    "HeaterCutOffTempLimit": 90,
    "HeaterCutInTempLimit": 80,
    "PCBCutOffTempLimit": 70,
    "PCBCutInTempLimit": 65,
    "OverVolatgeLimit": 68,
    "UnderVolatgeLimit": 50,
    "OverCurrentLimit": 25,
}

def getConfigStr():
    str = "{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
        config["VersionMinor"],
        config["VersionMajor"],
        config["VersionPatch"],
        config["HeaterRatedPower"],
        config["Heater1Wattage"],
        config["Heater2Wattage"],
        config["Heater3Wattage"],
        config["HeaterCutOffTempLimit"],
        config["HeaterCutInTempLimit"],
        config["PCBCutOffTempLimit"],
        config["PCBCutInTempLimit"],
        config["OverVolatgeLimit"],
        config["UnderVolatgeLimit"],
        config["OverCurrentLimit"],
    )
    print(str)
    return str

getConfigStr()