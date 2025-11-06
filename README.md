# IoT Telemetry Protocol

A lightweight UDP-based telemetry protocol for IoT devices that demonstrates:

- Server auto-discovery
- Real-time data transmission
- CSV logging
- Multiple device support

## Demo Video

Watch a 5-minute demonstration of the protocol in action:  
[Watch Demo Video]()\_

## Quick Start (5 minutes)

1. Make sure you have Python 3.8 or newer installed
2. Open two terminal windows
3. In terminal 1, run:
   ```bash
   python prototype_server.py
   ```
4. In terminal 2, run:
   ```bash
   python prototype_client.py
   ```
5. Watch as the client discovers the server and starts sending telemetry data

## What You'll See

- Server starts and listens for clients
- Client broadcasts to discover server
- Client connects and sends INIT message
- Temperature readings start flowing
- Server logs everything to CSV files

## Protocol Specification

### Message Types

1. INIT (0): Initial connection message
2. DATA (1): Data transmission message
3. HEARTBEAT (2): Connection keep-alive message (in complete version)

### Packet Structure

#### Prototype Version Header (10 bytes)

```
+------------+----------+-----------+------------+-------+
| Version/   | Device   | Sequence  | Timestamp  | Flags |
| Type (1B)  | ID (2B)  | Num (2B)  | (4B)      | (1B)  |
+------------+----------+-----------+------------+-------+
```

## Features

### Prototype Version

- Server auto-discovery using UDP broadcast
- Basic message transmission
- Simple header structure
- Real-time communication
- CSV logging of all messages

## Advanced Testing

To run automated tests with multiple clients:

```bash
python automated_test.py --clients 3
```

## Files Explained

- `prototype_server.py` - The UDP server that receives data
- `prototype_client.py` - A client that sends simulated sensor data
- `automated_test.py` - Script to test with multiple clients
- `telemetry_log.csv` - Log file with all received data
- `auto_script.csv` - Automated test results
