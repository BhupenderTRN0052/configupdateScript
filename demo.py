import can

try:
    bus = can.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=250000)

    msg = can.Message(arbitration_id=0x123, data=[0x01, 0x00, 0x00], is_extended_id=False)

    bus.send(msg)
    print("Message sent successfully")

except can.CanError as e:
    print(f"CAN send failed: {e}")
