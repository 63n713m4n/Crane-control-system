"""
Grade E: Crane Control System
Controls crane via Modbus to move parts from Source1 -> Process1 -> Sink
Simple single-part sequence
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import time
import json

# Modbus Addresses
class ModbusAddresses:
    # Sources
    SOURCE1_SENSOR = 17
    SOURCE2_SENSOR = 18

    # Process 1
    PROCESS1_RUN = 4
    PROCESS1_SENSOR = 21
    PROCESS1_IS_RUNNING = 19
    PROCESS1_RESET = 0

    # Process 2
    PROCESS2_RUN = 5
    PROCESS2_SENSOR = 22
    PROCESS2_IS_RUNNING = 20
    PROCESS2_RESET = 0

    # Crane
    CRANE_SET_X = 1
    CRANE_SET_Y = 2
    CRANE_POS_X = 15
    CRANE_POS_Y = 16
    CRANE_VACUUM = 3

# Initialize Modbus client
client = ModbusTcpClient('127.0.0.1')

def read_input(address):
    """Read a value from a Modbus holding register"""
    try:
        result = client.read_holding_registers(address=address, count=1)
        if result.isError():
            print(f"Error reading from address {address}")
            return None
        return result.registers[0]
    except Exception as e:
        print(f"Exception reading address {address}: {e}")
        return None

def write_output(address, value):
    """Write a value to a Modbus register"""
    try:
        result = client.write_register(address, value)
        if result.isError():
            print(f"Error writing {value} to address {address}")
            return False
        return True
    except Exception as e:
        print(f"Exception writing to address {address}: {e}")
        return False

def wait_for_position(target_x, target_y, tolerance=5, timeout=30):
    """Wait until crane reaches target position within tolerance"""
    print(f"  Waiting for crane to reach ({target_x}, {target_y})...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        current_x = read_input(ModbusAddresses.CRANE_POS_X)
        current_y = read_input(ModbusAddresses.CRANE_POS_Y)

        if current_x is None or current_y is None:
            time.sleep(0.1)
            continue

        if abs(current_x - target_x) <= tolerance and abs(current_y - target_y) <= tolerance:
            print(f"  Crane reached ({current_x}, {current_y})")
            return True

        time.sleep(0.1)

    print(f"  Timeout waiting for position ({target_x}, {target_y})")
    return False

def wait_for_part_at_source1(timeout=300):
    """Wait for a part to be present at Source1"""
    print("\n[WAITING] Waiting for part at Source1...")
    print("Please click 'Generate' button at Source1 in the simulation")
    start_time = time.time()

    while time.time() - start_time < timeout:
        sensor_value = read_input(ModbusAddresses.SOURCE1_SENSOR)

        if sensor_value == 1:
            print("[DETECTED] Part detected at Source1!")
            return True

        time.sleep(0.5)

    print("[TIMEOUT] No part detected at Source1")
    return False

def run_process1():
    """Start Process1 and wait for completion"""
    # Check if part is present
    sensor = read_input(ModbusAddresses.PROCESS1_SENSOR)
    if sensor != 1:
        print(f"[WARNING] Process1 sensor shows no part (value: {sensor})")

    # Start the process
    print("\n[PROCESS] Starting Process 1...")
    write_output(ModbusAddresses.PROCESS1_RUN, 1)
    time.sleep(1.0)

    # Wait for process to start
    print("[PROCESS] Waiting for Process 1 to start...")
    start_time = time.time()
    process_started = False
    while time.time() - start_time < 10:
        is_running = read_input(ModbusAddresses.PROCESS1_IS_RUNNING)
        if is_running == 1:
            print("[PROCESS] Process 1 is running")
            process_started = True
            break
        time.sleep(0.2)

    if not process_started:
        print("[WARNING] Process 1 didn't start, but continuing...")

    # Wait for process to complete
    print("[PROCESS] Waiting for Process 1 to complete...")
    start_time = time.time()
    while time.time() - start_time < 60:
        is_running = read_input(ModbusAddresses.PROCESS1_IS_RUNNING)
        if is_running == 0:
            print("[PROCESS] Process 1 completed!")
            # Turn off run signal
            write_output(ModbusAddresses.PROCESS1_RUN, 0)
            time.sleep(0.5)
            return True
        time.sleep(0.5)

    print("[TIMEOUT] Process 1 did not complete in time")
    write_output(ModbusAddresses.PROCESS1_RUN, 0)
    return False

def execute_action(action):
    """Execute a single action from the JSON file"""
    # Handle vacuum control
    if "vacuum" in action:
        vacuum_state = action["vacuum"]
        print(f"  Vacuum: {vacuum_state}")
        write_output(ModbusAddresses.CRANE_VACUUM, vacuum_state)
        time.sleep(0.8 if vacuum_state == 0 else 0.5)

    # Handle position movement
    if "setX" in action and "setY" in action:
        target_x = action["setX"]
        target_y = action["setY"]
        print(f"  Moving to ({target_x}, {target_y})")
        write_output(ModbusAddresses.CRANE_SET_X, target_x)
        write_output(ModbusAddresses.CRANE_SET_Y, target_y)
        wait_for_position(target_x, target_y)

    # Handle process wait
    if "wait_for_process" in action:
        time.sleep(0.5)  # Ensure crane is clear
        run_process1()

def load_sequence(filename):
    """Load action sequence from JSON file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get("actions", [])
    except FileNotFoundError:
        print(f"Error: File {filename} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}")
        return []

def main():
    """Main function for Grade E"""
    print("="*70)
    print(" "*20 + "GRADE E: Crane Control")
    print(" "*15 + "Source1 → Process1 → Sink")
    print("="*70)

    # Connect to Modbus
    print("\n[MODBUS] Connecting to 127.0.0.1...")
    if not client.connect():
        print("[ERROR] Failed to connect to Modbus server")
        return
    print("[MODBUS] Connected successfully")

    try:
        # Wait for a part at Source1
        if not wait_for_part_at_source1():
            print("\n[EXIT] No part available at Source1")
            return

        # Load sequence from JSON
        actions = load_sequence("crane_sequence_e.json")
        if not actions:
            print("\n[ERROR] No actions to execute")
            return

        print(f"\n[SEQUENCE] Loaded {len(actions)} actions")
        print("\n" + "="*70)
        print("Starting crane sequence...")
        print("="*70)
        time.sleep(1)

        # Execute each action
        for i, action in enumerate(actions, 1):
            print(f"\n[Action {i}/{len(actions)}] {action.get('description', 'No description')}")
            execute_action(action)

        print("\n" + "="*70)
        print(" "*20 + "SEQUENCE COMPLETED!")
        print("="*70)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Sequence stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        print("\n[MODBUS] Closing connection...")
        client.close()
        print("[MODBUS] Connection closed")

if __name__ == "__main__":
    main()
