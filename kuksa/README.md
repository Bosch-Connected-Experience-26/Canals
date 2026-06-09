# MDC Kuksa Example

A Python sample demonstrating how to interact with an [Eclipse KUKSA](https://github.com/eclipse-kuksa) Databroker via gRPC. The script takes remote control of a Mini Demo Car, runs a short demo sequence (start engine, accelerate, lights, stop), and subscribes to vehicle signal updates.

## Prerequisites

- Python 3.8+
- Network access to a running KUKSA Databroker instance (default: `192.168.56.6:55555`)

## Setup

1. Clone the repository and navigate into the project directory:

```bash
cd MDC_Kuksa_Example
```

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Edit the connection settings at the top of `kuksa_sample.py` if your Databroker runs on a different host or port:

```python
HOST = "192.168.56.6"
PORT = 55555
```

## Usage

Run the demo sequence:

```bash
python kuksa_sample.py
```

The script will:
1. Request takeover control of the Mini Demo Car
2. Start the engine
3. Accelerate to 50% pedal position
4. Stop (pedal to 0%)
5. Toggle low beam lights on/off
6. Stop the engine
7. Release control

Press `Ctrl+C` to stop the script.

## Project Structure

```
MDC_Kuksa_Example/
├── kuksa_sample.py    # Main demo script
├── requirements.txt   # Python dependencies
└── README.md          # This file
```
