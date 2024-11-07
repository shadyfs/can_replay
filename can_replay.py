import time
import json
import random
import threading
import can

with open("standard_messages.json", "r") as std_file:
    standard_messages = json.load(std_file)

with open("tp_messages.json", "r") as tp_file:
    tp_messages = json.load(tp_file)


def replay_standard_message(bus, can_id, details):
    """Replay a standard message independently at its own interval."""
    interval = details["average_interval"]
    data_list = details["data"]
    while True:
        data = random.choice(data_list)
        msg = can.Message(
            arbitration_id=int(can_id, 16), 
            data=bytes.fromhex(data), 
            is_extended_id=True
        )
        bus.send(msg)
        time.sleep(interval)


def replay_standard_messages(bus):
    """Start a separate thread for each standard message CAN ID."""
    for can_id, details in standard_messages.items():
        threading.Thread(target=replay_standard_message, args=(bus, can_id, details), daemon=True).start()


def find_tp_rts(sa, da):
    """Find the RTS message for the given source and destination addresses."""
    for rts_id, rts_data_list in tp_messages.items():
        if rts_id.startswith(f"1CEC{sa:02X}{da:02X}"):
            return rts_id, rts_data_list[0]
    return None, None


def find_tp_data(sa, da):
    """Find the Data Transfer (DT) messages for the given source and destination addresses."""
    data_messages = {}
    for data_id, data_payloads in tp_messages.items():
        if data_id.startswith(f"1CEB{sa:02X}{da:02X}"):
            for payload in data_payloads:
                packet_number = int(payload[:2], 16)  
                data_messages[packet_number] = payload
    return dict(sorted(data_messages.items())) 


def replay_tp_messages(bus):
    """State machine to handle TP message replay based on requests and CTS responses."""
    while True:
        msg = bus.recv()
        da = (msg.arbitration_id >> 8) & 0xFF  
        sa = msg.arbitration_id & 0xFF         
        pf = (msg.arbitration_id >> 16) & 0xFF  

        if pf == 0xEA:
            print(f"Received Request (EA) from SA={sa:02X} to DA={da:02X}")
            rts_id, rts_data = find_tp_rts(sa, da)
            if rts_id:
                rts_msg = can.Message(
                    arbitration_id=int(rts_id, 16),
                    data=bytes.fromhex(rts_data),
                    is_extended_id=True
                )
                bus.send(rts_msg)
                print(f"Sent RTS message: {rts_msg}")
                while True:
                    cts_msg = bus.recv()
                    pf_cts = (cts_msg.arbitration_id >> 16) & 0xFF 
                    da_cts = (cts_msg.arbitration_id >> 8) & 0xFF 
                    sa_cts = cts_msg.arbitration_id & 0xFF       
                    # print(f"Received CTS message: {cts_msg}")
                    # print(f"Extracted PF={pf_cts:02X}, DA={da_cts:02X}, SA={sa_cts:02X}")

                    if (
                        pf_cts == 0xEC and         
                        da_cts == da and          
                        sa_cts == sa and           
                        cts_msg.data[0] == 0x11    
                    ):
                        print(f"CTS received for packet transmission.")
                        data_messages = find_tp_data(sa, da)
                        for packet_number, data_payload in data_messages.items():
                            dt_msg = can.Message(
                                arbitration_id=int(rts_id.replace("EC", "EB"), 16), 
                                data=bytes.fromhex(data_payload),
                                is_extended_id=True
                            )
                            try:
                                bus.send(dt_msg)
                                print(f"Sent Data Packet {packet_number}: {dt_msg}")
                                time.sleep(0.1)  
                            except can.CanError as e:
                                print(f"Error sending packet {packet_number}: {e}")
                        break



if __name__ == "__main__":
    bus = can.Bus(interface="socketcan", channel="vcan0", receive_own_messages=False)
    
    try:
        # Start standard message replay
        replay_standard_messages(bus)
        
        # Handle TP message replay (state machine)
        replay_tp_messages(bus)
    except KeyboardInterrupt:
        pass
    finally:
        bus.shutdown()
