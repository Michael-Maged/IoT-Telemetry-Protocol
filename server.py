# server.py -- TinyTelemetry collector (demonstration)
import socket
import struct
import time
import csv
from collections import defaultdict

HEADER_FMT = '!BBBHHI'  # 11 bytes
HEADER_LEN = struct.calcsize(HEADER_FMT)

UDP_PORT = 50000

def now_ms():
    return int(time.time() * 1000)

class DeviceState:
    def __init__(self):
        self.last_seq = None
        self.received = set()

def parse_packet(data, addr):
    if len(data) < HEADER_LEN:
        return None
    hdr = struct.unpack(HEADER_FMT, data[:HEADER_LEN])
    version, msg_type, flags, device_id, seq, timestamp = hdr
    payload = data[HEADER_LEN:]
    return {
        'version': version, 'msg_type': msg_type, 'flags': flags,
        'device_id': device_id, 'seq': seq, 'timestamp': timestamp,
        'payload': payload, 'src': addr
    }

def process_data_pkt(pkt, devstate, arrival_time_ms):
    # payload layout: reading_count (1 byte) then reading_count * (type 1 byte + float 4 bytes)
    p = pkt['payload']
    duplicate = False
    gap = False
    if pkt['seq'] in devstate.received:
        duplicate = True
    else:
        # detect gap: compare to last_seq if exists
        if devstate.last_seq is not None:
            expected = (devstate.last_seq + 1) & 0xffff
            if pkt['seq'] != expected:
                gap = True
        devstate.received.add(pkt['seq'])
        devstate.last_seq = pkt['seq']

    readings = []
    if len(p) >= 1:
        rc = p[0]
        off = 1
        for i in range(rc):
            if off + 5 <= len(p):
                sensor_type = p[off]
                val = struct.unpack('!f', p[off+1:off+5])[0]
                readings.append((sensor_type, val))
                off += 5
            else:
                break
    return duplicate, gap, readings

def main(bind='0.0.0.0', port=UDP_PORT, csv_out='received.csv'):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind, port))
    print(f"Listening on {bind}:{port}")
    dev_states = defaultdict(DeviceState)
    # open CSV
    with open(csv_out, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['device_id','seq','timestamp_ms','arrival_time_ms','duplicate_flag','gap_flag','reading_count']) # msg type
        while True:
            data, addr = sock.recvfrom(4096)
            arrival = now_ms()
            pkt = parse_packet(data, addr)
            if not pkt:
                print("Short packet from", addr)
                continue
            dev = pkt['device_id']
            dstate = dev_states[dev]
            if pkt['msg_type'] == 0:  # INIT
                print(f"[{arrival}] INIT from device {dev} seq={pkt['seq']}")
                writer.writerow([dev, pkt['seq'], pkt['timestamp'], arrival, 0, 0, 0])
                f.flush()
            elif pkt['msg_type'] == 1:  # DATA
                dup, gap, readings = process_data_pkt(pkt, dstate, arrival)
                print(f"[{arrival}] DATA from {dev} seq={pkt['seq']} readings={len(readings)} dup={dup} gap={gap}")
                writer.writerow([dev, pkt['seq'], pkt['timestamp'], arrival, int(dup), int(gap), len(readings)])
                f.flush()
            elif pkt['msg_type'] == 2:  # HEARTBEAT
                print(f"[{arrival}] HEARTBEAT from {dev} seq={pkt['seq']}")
                writer.writerow([dev, pkt['seq'], pkt['timestamp'], arrival, 0, 0, 0])
                f.flush()
            else:
                print("Unknown msg type", pkt['msg_type'])

if __name__ == '__main__':
    main()
