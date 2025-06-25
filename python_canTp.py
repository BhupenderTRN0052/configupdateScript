import can
from time import sleep, time
import threading
from queue import Queue, Empty
import os
from datetime import datetime
import can.interfaces.pcan
class CANTransport:
    def __init__(self):
        self.can_bus = None
        self.error_logger = None
        self.tx_thread = None
        self.rx_thread = None
        self.log_thread = None
        self.running = False
        self.tx_queue = []
        self.log_queue = []  # Queue to store log messages
        self.rx_queue = Queue()  # Queue to store received messages
        self.rx_filters = []
        self.isotp_stack = None  # Common ISO-TP stack
        self.can_tp_send = False

    def __get_can_connection(self):
        # Create a CAN bus connection
        self.can_bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS1', bitrate=250_000)
        print("CAN connection established.")

    def start_can_connection(self):
        if self.can_bus is None:
            self.__get_can_connection()

    def set_can_filters(self, *args):
        if len(args) == 0:
            raise ValueError("At least one CAN ID must be provided.")

        filters = []
        for can_id in args:
            filters.append({
                "can_id": can_id,
                "can_mask": 0x7FF,
                "extended": False
            })
        self.can_bus.set_filters(filters)

    def clear_can_filters(self):
        self.can_bus.set_filters([])

    def start_can_threads(self):
        if not self.running:
            self.running = True
            self.tx_thread = threading.Thread(target=self.__tx_worker, daemon=True)
            self.rx_thread = threading.Thread(target=self.__rx_worker, daemon=True)
            self.log_thread = threading.Thread(target=self.__log_worker, daemon=True)
            self.tx_thread.start()
            self.rx_thread.start()
            self.log_thread.start()
            print("Threads started for Transmission and Reception.")

    def stop_threads(self):
        self.running = False
        if self.tx_thread:
            self.tx_thread.join()
        if self.rx_thread:
            self.rx_thread.join()
        if self.log_thread:
            self.log_thread.join()
        self.close_can_connection()
        print("Threads stopped.")

    def __tx_worker(self):
        while self.running:
            if self.tx_queue:
                msg = self.tx_queue.pop(0)
                self.can_bus.send(msg)

    def __rx_worker(self):
        while self.running:
            if not self.can_tp_send:
                try:
                    data = self.can_bus.recv()
                    self.log_message(f"Received: {data}")
                    self.rx_queue.put(data)
                except Exception as e:
                    print(f"Exception in RX thread: {e}")

    def __log_worker(self):
        """Worker function to process log messages and save them to files."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_name = f"log_{timestamp}.txt"
        while self.running:
            if self.log_queue:
                # Pop the first log from the queue safely
                log = self.log_queue.pop(0)
                # Create a logs directory if it doesn't exist
                if not os.path.exists("logs"):
                    os.makedirs("logs")

                # Save the log to a file in the logs directory
                log_file_path = os.path.join("logs", log_file_name)
                with open(log_file_path, "a") as log_file:
                    log_file.write(log + "\n")
            else:
                # Sleep briefly if the queue is empty to avoid high CPU usage
                sleep(0.1)
                

    def close_can_connection(self):
        if self.can_bus is not None:
            self.can_bus.shutdown()
            self.can_bus = None

    def my_error_handler(self, error):
        print(f"IsoTp error happened: {error.__class__.__name__} - {str(error)}")


    #def send_message_on_can_tp(self, txid, rxid, message: str, timeout , rx_flow_control_timeout_ms, cycle_time_in_s,encoded):
        #self.can_tp_send = True
        #temp_filter = self.can_bus.filters()
        #self.can_bus.set_filters([])    # Disable all filters
        #self.can_bus.set_filters(rxid)    # Enable all filters
        #addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=rxid, txid=txid)
        #params = {
        #    'blocking_send' : True,
        #    'rx_flowcontrol_timeout': rx_flow_control_timeout_ms,
        #    'override_receiver_stmin':cycle_time_in_s #this is in seconds
        #}
        #stack = isotp.CanStack(self.can_bus, address=addr, error_handler=self.my_error_handler, params=params)
        #res = None
        #try:
        #    stack.start()
        #    if(not encoded):
        #        byte_msg = message.encode('utf-8')
        #    else:
        #        byte_msg = message
        #    stack.send(byte_msg, send_timeout=timeout)    # Blocking send, raise on error
            #print(f"Payload transmission successfully completed: {message}")     # Success is guaranteed because send() can raise
        #    res = True
        #except isotp.BlockingSendFailure:   # Happens for any kind of failure, including timeouts
        #    print("Send failed")
        #    res = False
        #finally:
        #    """ stack.stop() """
        #    self.can_tp_send = False
            
        #    return res
    
    def send_message_on_can_tp2(self, txid, rxid, message: str, rx_flow_control_timeout_s, cycle_time_in_s):
        message_size = len(message)
        frames = self._segment_message(message)
        #print(txid)
        
        # Send the First Frame
        self._send_first_frame(txid,message_size, frames[0])
        self.log_message("First Frame sent successfully")
        fc_frame = self._wait_for_flow_control(rxid,rx_flow_control_timeout_s)
        if not fc_frame:
            """ print("Flow Control Timeout") """
            return False
        
        # Parse Flow Control
        """ block_size, st_min = self._parse_flow_control(fc_frame) """
        self._send_consecutive_frames(frames[1:],txid, 8, cycle_time_in_s)
        self.log_message("Message sent successfully")
        return True
        
    def _segment_message(self, message):
        """Splits the message into chunks for First Frame (FF) and Consecutive Frames (CF)."""
        if not message:
            return []

        first_frame_data_length = 6  # First Frame can contain up to 6 bytes of data
        consecutive_frame_data_length = 7  # Consecutive Frames can contain up to 7 bytes

        # Split the message into FF and CF
        first_frame = message[:first_frame_data_length]
        remaining_data = message[first_frame_data_length:]
        consecutive_frames = [remaining_data[i:i + consecutive_frame_data_length] for i in range(0, len(remaining_data), consecutive_frame_data_length)]

        return [first_frame] + consecutive_frames

    def _send_first_frame(self, tx_id, message_size, first_chunk):
        """
        Send the first frame with the message size and initial data.

        Parameters:
        - tx_id: Transmit CAN ID
        - message_size: Total size of the message in bytes
        - first_chunk: First 6 bytes of the message data
        """
        # Split the message size into 12-bit length (split into 2 nibbles)
        size_high = (message_size >> 8) & 0x0F  # High nibble of the message size
        size_low = message_size & 0xFF          # Lower byte of the message size

        # Construct the First Frame (FF)
        header = 0x10 | size_high               # First byte: 0x1X where X = high nibble of size
        data = [header, size_low] + list(first_chunk)  # Header + size low + first 6 bytes of data
        data = data[:8]  # Ensure frame is 8 bytes long

        # Debug print for verification
        """ print(f"First Frame: {data}") """

        # Send the First Frame to the CAN bus
        self.queue_message(tx_id, data)

    def _wait_for_flow_control(self,rx_id, timeout):
        """Wait for a Flow Control frame."""
        val,data = self.receive_data_for_can_id(rx_id, timeout)
        if val:
            if data[0] & 0xF0 == 0x30:
                return True
        return False

    def _parse_flow_control(self, fc_frame):
        """Parse the Flow Control frame."""
        block_size = fc_frame[1]
        st_min = fc_frame[2] / 1000.0  # Convert milliseconds to seconds
        return block_size, st_min

    def _send_consecutive_frames(self, frames,tx_id, block_size, st_min):
        """Send consecutive frames as per Flow Control."""
        seq_num = 0
        """ 
        for i, frame in enumerate(frames):
            if i % block_size == 0 and i != 0:
                print("Waiting for next flow control")
                fc_frame = self._wait_for_flow_control(1.0)
                if not fc_frame:
                    raise Exception("Flow Control Timeout")
                block_size, st_min = self._parse_flow_control(fc_frame)
             """
        for i, frame in enumerate(frames):
            data = [0x20 | (seq_num & 0x0F)] + list(frame)
            data = data[:8]
            self.queue_message(tx_id, data)
            seq_num = (seq_num + 1) & 0x0F  # Sequence number rolls over after 0x0F


    """ def receive_data_on_can_tp(self, timeout):
        if not self.isotp_stack:
            raise RuntimeError("ISO-TP stack is not set up.")

        res, data = 0, None
        try:
            stack_read_time = time() + timeout
            while time() < stack_read_time:
                data = self.isotp_stack.recv()
                if data is not None:
                    print(f"Data received: {data}")
                    break
                sleep(0.005)

            if data is None:
                res = 1
                print("No data received within the timeout period.")
        except Exception as e:
            print(f"Exception occurred: {e}")
            res = 2
        return res, data """

    def queue_message(self, can_id, message):
        #print(f"can id:{can_id}, message: {message}")
        msg = can.Message(arbitration_id=can_id, data=message, is_extended_id=False)
        self.tx_queue.append(msg)

    def log_message(self, message):
        message_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{message_timestamp}] {message}\n"
        self.log_queue.append(log_entry)

    def receive_data_for_can_id(self, can_id, timeout):
        start_time = time()
        while time() - start_time < timeout:
            try:
                # Ensure get() does not block indefinitely by setting a small timeout
                data = self.rx_queue.get(timeout=0.1)
                if data.arbitration_id == can_id:
                    return True, data.data
            except Empty:  # Catch the Empty exception correctly
                # Continue looping until the overall timeout expires
                pass
        return False, None
