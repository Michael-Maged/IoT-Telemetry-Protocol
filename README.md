# IoT Telemetry Protocol

A simple implementation of a UDP-based telemetry protocol for IoT devices.

## Project Overview

This project implements a lightweight telemetry protocol for IoT devices using UDP. It includes two versions:

- A prototype version for basic communication

### Protocol Specification

#### Message Types

1. INIT (0): Initial connection message
2. DATA (1): Data transmission message
3. HEARTBEAT (2): Connection keep-alive message (in complete version)

#### Packet Structure

##### Prototype Version Header (10 bytes)

```
+------------+----------+-----------+------------+-------+
| Version/   | Device   | Sequence  | Timestamp  | Flags |
| Type (1B)  | ID (2B)  | Num (2B)  | (4B)      | (1B)  |
+------------+----------+-----------+------------+-------+
```

### Features

#### Prototype Version

- Server auto-discovery using UDP broadcast
- Basic message transmission
- Simple header structure
- Real-time communication


### How It Works

1. **Server Setup**

   - Binds to a UDP port (9999 for prototype, 50000 for complete)
   - Waits for incoming connections

2. **Client Operation**

   - Discovers server (in prototype version)
   - Sends INIT message
   - Transmits data packets
   - Includes sequence numbers for tracking

3. **Data Handling**
   - Server logs all received packets
   - Tracks sequence numbers to detect missing packets
   - Records timestamps for timing analysis

### Usage

1. **Start the Server**

   ```bash
   python prototype_server.py
   ```

2. **Run the Client**
   ```bash
   python prototype_client.py
   ```


### Implementation Details

#### Prototype Version

- Simple UDP communication
- Basic header structure
- Server discovery mechanism
- Text message transmission

### Error Handling

- Duplicate packet detection
- Sequence gap detection
- Malformed packet handling
- Buffer overflow prevention