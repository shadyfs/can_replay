import re
import json
from collections import defaultdict

log_pattern = re.compile(r'\((\d+\.\d+)\) can0 ([0-9A-F]{8})#([0-9A-F]*)')
standard_messages = defaultdict(lambda: {"data": set(), "average_interval": None})
tp_messages = defaultdict(set)

def extract_pgn_sa(can_id):
    can_id = int(can_id, 16)
    pgn = (can_id >> 8) & 0xFFFF
    sa = can_id & 0xFF
    pf = (pgn >> 8) & 0xFF
    return pgn, pf, sa

last_timestamps = {}
interval_sums = defaultdict(float)
interval_counts = defaultdict(int)

DEFAULT_INTERVAL = 1.0 

log_file = "Sensor_CAN.log" 

with open(log_file, 'r') as file:
    for line in file:
        match = log_pattern.match(line.strip())
        if match:
            timestamp, can_id, data = match.groups()
            timestamp = float(timestamp)
            
            pgn, pf, sa = extract_pgn_sa(can_id)
            
            if sa == 0x00:
                continue  
            
            if pf in {0xEA, 0xEB, 0xEC}: 
                tp_messages[can_id].add(data)
            else:
                standard_messages[can_id]["data"].add(data)
                
                if can_id in last_timestamps:
                    interval = timestamp - last_timestamps[can_id]
                    interval_sums[can_id] += interval
                    interval_counts[can_id] += 1
                last_timestamps[can_id] = timestamp

for can_id in standard_messages:
    if interval_counts[can_id] > 0:
        standard_messages[can_id]["average_interval"] = (
            interval_sums[can_id] / interval_counts[can_id]
        )
    else:
        standard_messages[can_id]["average_interval"] = DEFAULT_INTERVAL

standard_json = {
    can_id: {
        "data": list(entry["data"]),
        "average_interval": entry["average_interval"]
    }
    for can_id, entry in standard_messages.items()
}

tp_json = {
    can_id: list(data_list)
    for can_id, data_list in tp_messages.items()
}

with open("standard_messages.json", 'w') as std_file:
    json.dump(standard_json, std_file, indent=4)

with open("tp_messages.json", 'w') as tp_file:
    json.dump(tp_json, tp_file, indent=4)

print("Standard messages saved to 'standard_messages.json'")
print("TP messages saved to 'tp_messages.json'")
