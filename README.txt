IoT Telemetry Protocol - Quick Start Guide
=======================================

This is a lightweight UDP-based telemetry protocol for IoT devices that demonstrates:
- Server auto-discovery
- Real-time data transmission
- CSV logging
- Multiple device support

Quick Start (5 minutes)
----------------------
1. Make sure you have Python 3.8 or newer installed
2. Open two terminal windows
3. In terminal 1, run: python prototype_server.py
4. In terminal 2, run: python prototype_client.py
5. Watch as the client discovers the server and starts sending telemetry data!

Demo Video
----------
Watch a 5-minute demonstration of the protocol in action:
https://youtu.be/your_video_id_here    [REPLACE WITH YOUR ACTUAL VIDEO LINK]

What You'll See
--------------
- Server starts and listens for clients
- Client broadcasts to discover server
- Client connects and sends INIT message
- Temperature readings start flowing
- Server logs everything to CSV files

Advanced Testing
---------------
To run automated tests with multiple clients:
python automated_test.py --clients 3

Files Explained
--------------
prototype_server.py - The UDP server that receives data
prototype_client.py - A client that sends simulated sensor data
automated_test.py  - Script to test with multiple clients
telemetry_log.csv  - Log file with all received data
auto_script.csv    - Automated test results


