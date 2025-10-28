# client.py -- TinyTelemetry sensor demo
import socket
import struct
import time
import random

HEADER_FMT = '!BBBHHI'  # 11 bytes
HEADER_LEN = struct.calcsize(HEADER_FMT)

def now_ms():
    return int(time.time() * 1000)

def make_header(version, msg_type, flags, device_id, seq):
    ts = now_ms() & 0xffffffff
    return struct.pack(HEADER_FMT, version, msg_type, flags, device_id, seq, ts)

def make_data_packet(device_id, seq, readings):
    # readings: list of tuples (sensor_type:int, float_value:float)
    hdr = make_header(1, 1, 1, device_id, seq)
    rc = len(readings)
    payload = bytes([rc])
    for st, val in readings:
        payload += bytes([st]) + struct.pack('!f', float(val))
    return hdr + payload

def main(server='127.0.0.1', port=50000, device_id=42, interval=1.0, duration=60):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    # INIT
    init_pkt = make_header(1, 0, 0, device_id, seq)
    sock.sendto(init_pkt, (server, port))
    seq = (seq + 1) & 0xffff
    start = time.time()
    while time.time() - start < duration:
        # generate 1-3 readings
        readings = []
        for i in range(random.randint(1,3)):
            sensor_type = 1  # temperature
            value = 20.0 + random.random()*5.0
            readings.append((sensor_type, value))
        pkt = make_data_packet(device_id, seq, readings)
        sock.sendto(pkt, (server, port))
        print(f"[{int(time.time())}] sent seq={seq} readings={len(readings)}")
        seq = (seq + 1) & 0xffff
        time.sleep(interval)
    # final heartbeat
    hb = make_header(1, 2, 0, device_id, seq)
    sock.sendto(hb, (server, port))
    print("Done.")


if __name__ == '__main__':
    main()