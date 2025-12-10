# IoT Telemetry Protocol Testing

## Cross-Platform Setup

### Windows Development
1. **Install WSL2** (for Linux compatibility testing):
   ```cmd
   wsl --install
   ```

2. **Install Network Testing Tools**:
   - **Clumsy**: Download from https://jagt.github.io/clumsy/ for network simulation
   - **Wireshark**: For packet analysis
   - **WSL2**: For running Linux tests

3. **WSL2 Network Tools Setup**:
   ```bash
   sudo apt update
   sudo apt install -y iproute2 iperf3 netcat-openbsd
   ```

### Running Tests

#### Windows (Development)
```cmd
# Baseline test
tests\run_baseline.bat

# Packet loss test (requires Clumsy)
tests\run_loss_5.bat

# Automated test
python tests\automated_test.py --clients 2
```

#### Linux/WSL2 (Production)
```bash
# Baseline test
./tests/run_baseline.sh

# Packet loss test
./tests/run_loss_5.sh

# Network emulation examples
sudo tc qdisc add dev eth0 root netem delay 100ms
sudo tc qdisc add dev eth0 root netem loss 10%
```

### File Structure
```
telemetry_tests/
├── project/
│   ├── oop_server.py    # Server implementation
│   ├── oop_client.py    # Client implementation
│   └── client_ids.txt   # Device ID counter
├── tests/
│   ├── *.sh            # Linux test scripts
│   ├── *.bat           # Windows test scripts
│   └── automated_test.py
├── analysis/
│   └── metrics.py      # Performance analysis
└── results/            # Test output logs
```

### Network Testing
- **Development**: Use Clumsy for manual network condition simulation
- **Validation**: Use WSL2 with `tc netem` for automated/reproducible tests
- **Analysis**: Use Wireshark for protocol debugging

### Important Notes
- Ensure code runs unchanged in Linux before submission
- Use relative paths for cross-platform compatibility
- Test with both Windows and Linux environments