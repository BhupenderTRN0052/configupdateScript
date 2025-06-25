import struct
import zlib

config = {
    "VersionMajor": 0,
    "VersionMinor": 0,
    "VersionPatch": 1,
    "RatedPower": 1200,
    "Heater1Wattage": 530,
    "Heater2Wattage": 300,
    "Heater3Wattage": 440,
    "TempOffset": 0,
    "HeaterTemperature": 90,
    "PCBTemperature": 70,
    "UnderVolatgeLimit": 50,
    "OverVolatgeLimit": 68,
    "OverCurrentLimit": 25,
}

def configCrc():
    data = [
        config["VersionMinor"],
        config["VersionMajor"],
        config["VersionPatch"],
        config["RatedPower"],
        config["Heater1Wattage"],
        config["Heater2Wattage"],
        config["Heater3Wattage"],
        config["TempOffset"],
        config["HeaterTemperature"],
        config["PCBTemperature"],
        config["UnderVolatgeLimit"],
        config["OverVolatgeLimit"],
        config["OverCurrentLimit"],
    ]
    byte_data = byte_array = struct.pack("I" * len(data), *data)
    crc32Config = zlib.crc32(byte_data)
    return crc32Config

def getConfigStr():
    str = "{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
        config["VersionMinor"],
        config["VersionMajor"],
        config["VersionPatch"],
        config["RatedPower"],
        config["Heater1Wattage"],
        config["Heater2Wattage"],
        config["Heater3Wattage"],
        config["TempOffset"],
        config["HeaterTemperature"],
        config["PCBTemperature"],
        config["UnderVolatgeLimit"],
        config["OverVolatgeLimit"],
        config["OverCurrentLimit"],
        configCrc()
    )
    print(str)
    return str

getConfigStr()