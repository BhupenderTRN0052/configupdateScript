import python_canTp
from python_canTp import CANTransport
import os
from enum import Enum
import binascii
import struct
from time import sleep
import progressbar
import can.interfaces.pcan

class StatusCodes(Enum):
    STATUS_CODE_FAILED = 0
    STATUS_CODE_SUCCESS_MESS = 1
    STATUS_CODE_CAN_TP_TIMEOUT = 2
    APP_CLEAR_FAILED = 3
    CRC_MISMATCH = 4
    FLASH_WRITE_ERROR = 5
    STATUS_CODE_TRANSFER_COMPLETE = 6
    STATUS_CODE_CERTIFICATE_TX_COMPLETE = 7
    STATUS_CODE_VERIFICATION_FAILED = 8
    STATUS_CODE_FILE_NOT_PRESENT = 9
    STATUS_CODE_DOWNLOAD_FAIL = 10
    STATUS_CODE_OTA_ALREADY_PROGRESS = 11
    STATUS_CODE_NO_RESPONSE_ECU = 12
    STATUS_CODE_SESSION_NOT_SET = 13
    STATUS_CODE_INVALID_OTA = 14
    STATUS_CODE_FLASH_ALREADY_WRITTEN = 15

class Device(Enum):
    STARK = 0
    XAVIER = 4
    LAPTOP = 9
    SOLARCORE = 7

FOTA_MSG = 0
COTA_MSG = 1
VERSION_CAN_ID = 0x7A1
OTA_CAN_ID = 0x6FA
FOTA_INIT = [9, 9, 1, 2, 9]
COTA_INIT = [9, 9, 1, 4, 9]
FOTA_DONE = [9, 9, 1, 5, 9]
COTA_DONE = [9, 9, 1, 0xA, 9]
major = 0
minor = 0
patch = 0
build = 0
cfg = 0
app = 0
XAVIER_OTA_BUS_ID = 0x555

def transmit_binaries_with_ack(can, content, ota_type, bus_id, device):
    chunk_size = 512
    total_chunks = (len(content) + chunk_size - 1) // chunk_size  # Calculate total number of chunks
    errorValue = 0 
    class FloatPercentage(progressbar.Widget):
        def update(self, pbar):
            return f"{pbar.percentage():.2f}%"  # Show percentage with 2 decimal places
    bar = progressbar.ProgressBar(maxval=100, \
    widgets=[progressbar.Bar('=', '[', ']'), ' ', FloatPercentage()])
    bar.start()
    for chunk_index in range(total_chunks):
        start = chunk_index * chunk_size
        chunk = content[start:start + chunk_size]
        crc32 = binascii.crc32(chunk) & 0xFFFFFFFF
        offset = start
        crc32_bytes = crc32.to_bytes(4, byteorder='little')  # Convert CRC32 to 4 bytes
        offset_bytes = offset.to_bytes(4, byteorder='little')  # Convert offset to 4 bytes

        bin_message = bytes([ota_type]) + crc32_bytes + offset_bytes + chunk
        # Prepare binary message with correct formatting (ota_type, crc32, offset, and chunk)
        #bin_message = struct.pack(f"IIIs", ota_type, crc32, offset, chunk)

        #print(len(bin_message))
        retry_count = 0
        sent = False

        while retry_count < 10:
            if(can.send_message_on_can_tp2(bus_id, bus_id + 1, bin_message,2,0.0001)):
                id_rx, data = can.receive_data_for_can_id(OTA_CAN_ID, 2)
                
                if id_rx:
                    can.log_message("id_rx")
                    if (data[0] == device and data[1] == 9 and data[2] == 0 and
                        (data[3] == 1 or data[3] == StatusCodes.STATUS_CODE_FLASH_ALREADY_WRITTEN.value)):
                        sent = True
                        retry_count = 0
                        break
                    elif data[3] == StatusCodes.STATUS_CODE_FAILED.value:
                        errorValue = data[4]
                        break
                    else:
                        errorValue = data[3]
                        retry_count += 1
                else:
                    can.log_message("no id_rx")
                    retry_count += 1
                    errorValue = 1000
            else:
                can.log_message("send failed")
                retry_count +=1
                errorValue = 10000
        if not sent:
            print(f"Failed to send chunk {chunk_index + 1}/{total_chunks} after {retry_count} retries due to errorValue {errorValue}.")
            return 0,errorValue
        # Display progress
        progress = ((chunk_index + 1) / total_chunks) * 100
        bar.update(progress)
        #can.log_message(f"Progress: {progress:.2f}% ({chunk_index + 1}/{total_chunks})/r")

    #print("All chunks transmitted successfully!")
    bar.finish()
    return 1,0


def get_xavier_version(can, device):
    global major, minor, patch, build, cfg, app
    if can is None:
        print("Failed to initialize CAN")
        return False  # Fail immediately if CAN is not initialized
    app = 0
    attempt = 0
    max_attempts = 100  # Set the maximum number of attempts
    
    while attempt < max_attempts:
        try:
            # Send/receive data from the CAN bus depending on the selected device.
            # Replace this with actual communication logic.
            gotID, value = can.receive_data_for_can_id(VERSION_CAN_ID, 1)
            if gotID:
                # print(device)
                # print(value)
                if value[0] == device:
                    major = value[1]
                    minor = value[2]
                    patch = value[3]
                    build = value[4]
                    cfg = value[5]
                    app = value[7]
                    print("Version retrieved successfully.")
                    return True  # Success, return True
                else:
                    #print(f"Unexpected value received: {value[0]} at attempt {attempt + 1}")
                    can.log_message("Error: Unexpected value received: {value[0]} at attempt {attempt + 1}")    
            else:
                #print(f"No data received at attempt {attempt + 1}")
                can.log_message("Error: No data received at attempt {attempt + 1}")
        except Exception as e:
            print(f"Error while getting version: {e}")

        # Increment the attempt count and try again
        attempt += 1
        #print(f"Retrying... (Attempt {attempt}/{max_attempts})")

    print("Failed to get the version after 10 attempts.")
    return False  # Fail after 10 attempts


if __name__ == "__main__":
    can = CANTransport()
    # can.__init__()
    can.start_can_connection()
    can.set_can_filters(OTA_CAN_ID,XAVIER_OTA_BUS_ID+1,VERSION_CAN_ID)
    can.start_can_threads()
    """ print("Select Device : \n4.Xavier \n0.Stark \n")
    device_name = input("Enter the device name: ").strip().lower() """
    device_name = "solarcore"
    print(f"Selected device is {device_name}")
    device_val = Device[device_name.upper()]
    device = device_val.value
    sleep(2)
        #set can filters according to ecu here
    can.clear_can_filters()
    can.set_can_filters(OTA_CAN_ID,XAVIER_OTA_BUS_ID+1)
    if(get_xavier_version(can,device)):
        print(f"Found Version {major:2x},{minor:2x},{patch:2x}")
        print(f"Build Type {build} -> not using right now")
        print(f"config version {cfg}")
        print(f"Current App {app} -> not using right now")
        print("Enter 1 for Firmware Update or 2 for Config Update")
        update_type = int(input())
        if(update_type == 1):
            print("Selected Firmware Update")
            if(build == 1):#TODO: change this
                print("The device is in debug build, Please flash it to non debug build!")
                input("Press Enter to continue...")
                exit(10)
            else:
                version_input = input("Enter version (e.g., 0.1.2): ")
                version_components = version_input.split('.')
                version_numbers = [int(component,16) for component in version_components]
                major = version_numbers[0]
                minor = version_numbers[1]
                patch = version_numbers[2]
                dir = os.getcwd()
                ota_dir = os.path.join(dir, 'package')
                if(app == 1):
                    app_name= f"{device_name}-threadx-app2.bin"
                else:
                    app_name = f"{device_name}-threadx-app1.bin"
                print(f"finding app {app_name}")
                file_dir = os.path.join(ota_dir, f"v{major:02x}.{minor:02x}.{patch:02x}")
                file_bin_dir = os.path.join(file_dir, "bin")
                bin_dir = os.path.join(file_bin_dir,app_name)
                if os.path.exists(bin_dir):
                    with open(bin_dir, "rb") as source_file:
                        app_bin_content = source_file.read()
                        filesize = len(app_bin_content)
                        print(f"file size of the binary is {filesize}")
                        FOTA_INIT[1] = device
                        FOTA_INIT[4] = device
                    can.set_can_filters(OTA_CAN_ID,XAVIER_OTA_BUS_ID+1)
                    can.queue_message(OTA_CAN_ID,FOTA_INIT)
                    idRx,data=can.receive_data_for_can_id(OTA_CAN_ID,30)
                    if idRx:
                        if(data[0] ==device and data[1] == 9 and  data[3] == 1):
                            print("ota init successful")
                            txComplete,errorCode = transmit_binaries_with_ack(can,app_bin_content,FOTA_MSG,XAVIER_OTA_BUS_ID,Device.XAVIER.value)
                            if(txComplete == 1):
                                print("Binary Transfer Complete!")
                                print("switching partition")
                                FOTA_DONE[1] = device
                                FOTA_DONE[4] = device
                                can.log_message("sending fota done")
                                can.queue_message(OTA_CAN_ID,FOTA_DONE)
                                idRx,data=can.receive_data_for_can_id(OTA_CAN_ID,10)
                                if idRx:
                                    if(data[0] ==device and data[1] == 9 and  data[3] == 1):
                                        print("OTA complete! Getting New Xavier Version")
                                        sleep(20)
                                        can.set_can_filters(VERSION_CAN_ID)
                                        if(get_xavier_version(can,device)):
                                            print(f"Found Version {major:2x},{minor:2x},{patch:2x}")
                                            print(f"config version {cfg}")
                                            print(f"Current App {app}")
                                    else:
                                        print(f"switching partition failed due to error {data[3]}")
                        else:
                            print(f"ota failed due to ota not being initiated by Ecu")
                    else:
                        print("OTA init Failed")
                        input("Press enter to Continue")
                        exit(100)
                else:
                    print(f"file {bin_dir} not found ")
                
        elif(update_type == 2):
            version_input = input("Enter Config version (e.g., 14): ")
            dir = os.getcwd()
            ota_dir = os.path.join(dir, 'package')
            print(f"finding config {version_input}")
            bin_dir = os.path.join(ota_dir, f"v{version_input}_config.txt")
    
            # Check if the directory exists
            if os.path.exists(bin_dir):
                with open(bin_dir, "rb") as source_file:
                    app_bin_content = source_file.read()
                    filesize = len(app_bin_content)
                    print(f"file size of the binary is {filesize}")
                    COTA_INIT[1] = device
                    COTA_INIT[4] = device
                    can.set_can_filters(OTA_CAN_ID,XAVIER_OTA_BUS_ID+1)
                    can.queue_message(OTA_CAN_ID,COTA_INIT)
                    idRx,data=can.receive_data_for_can_id(OTA_CAN_ID,10)
                    if idRx:
                        if(data[0] == device and data[1] == 9 and  data[3] == 1):
                            print("cota init successful")
                            txComplete,errorCode = transmit_binaries_with_ack(can,app_bin_content,COTA_MSG,XAVIER_OTA_BUS_ID,Device.XAVIER.value)
                            if(txComplete == 1):
                                    sleep(20)
                                    print("Binary Transfer Complete!")
                                    print("Upgrading Config")
                                    COTA_DONE[1] = device
                                    COTA_DONE[4] = device
                                    can.queue_message(OTA_CAN_ID,COTA_DONE)
                                    idRx,data=can.receive_data_for_can_id(OTA_CAN_ID,10)
                                    if idRx:
                                        if(data[0] ==device and data[1] == 9 and  data[3] == 1):
                                            print("COTA complete! Getting New Xavier Config Version")
                                            sleep(20)
                                            can.set_can_filters(VERSION_CAN_ID)
                                            if(get_xavier_version(can,device)):
                                                print(f"Found Version {major:2x},{minor:2x},{patch:2x}")
                                                print(f"config version {cfg}")
                                                print(f"Current App {app}")
                                        else:
                                            print(f"Config Update failed due to error {data[3]}")
                        else:
                            print(f"cota failed due to ota not being initiated by Ecu")
                    else:
                        print("COTA init Failed")
                        input("Press enter to Continue")
                        exit(100)
            else:
                print(f"file {bin_dir} not found ")

    input("Press Enter to continue...")
    exit(10)

