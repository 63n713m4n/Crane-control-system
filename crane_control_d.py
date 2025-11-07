"""
Grade D: Crane Control System with Queue
Handles multiple Type 1 parts from Source1 with queue system
Source1 -> Process1 -> Sink (with queue management)
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import time
import json
from collections import deque

# Modbus Addresses
class ModbusAddresses:
    SOURCE1_SENSOR = 17
    SOURCE2_SENSOR = 18
    PROCESS1_RUN = 4
    PROCESS1_SENSOR = 21
    PROCESS1_IS_RUNNING = 19
    PROCESS1_RESET = 0
    PROCESS2_RUN = 5
    PROCESS2_SENSOR = 22
    PROCESS2_IS_RUNNING = 20
    PROCESS2_RESET = 0
    CRANE_SET_X = 1
    CRANE_SET_Y = 2
    CRANE_POS_X = 15
    CRANE_POS_Y = 16
    CRANE_VACUUM = 3

# Initialize Modbus client
client = ModbusTcpClient('127.0.0.1')

# Global queue for parts
part_queue = deque()
part_id_counter = 0

def read_input(address):
    """Read a value from a Modbus holding register"""
    try:
        result = client.read_holding_registers(address=address, count=1)
        if result.isError():
            return None
        return result.registers[0]
    except Exception as e:
        return None

def write_output(address, value):
    """Write a value to a Modbus register"""
    try:
        result = client.write_register(address, value)
        return not result.isError()
    except Exception as e:
        return False

def wait_for_position(target_x, target_y, tolerance=5, timeout=30):
    """Wait until crane reaches target position"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_x = read_input(ModbusAddresses.CRANE_POS_X)
        current_y = read_input(ModbusAddresses.CRANE_POS_Y)
        if current_x is not None and current_y is not None:
            if abs(current_x - target_x) <= tolerance and abs(current_y - target_y) <= tolerance:
                return True
        time.sleep(0.1)
    return False

def check_for_new_parts():
    """Check Source1 for new parts and add to queue"""
    global part_id_counter

    # Check Source1 sensor
    source1_sensor = read_input(ModbusAddresses.SOURCE1_SENSOR)

    if source1_sensor == 1:
        # Part detected at Source1
        # Check if this part is already in queue (avoid duplicates)
        if not any(p['location'] == 'source1' and p['status'] == 'waiting' for p in part_queue):
            part_id_counter += 1
            part = {
                'id': part_id_counter,
                'type': 1,
                'location': 'source1',
                'status': 'waiting'
            }
            part_queue.append(part)
            print(f"\n[QUEUE] New part #{part['id']} detected at Source1")
            print(f"[QUEUE] Queue size: {len(part_queue)}")
            return True

    return False

def execute_sequence(sequence_actions):
    """Execute a sequence of actions"""
    for action in sequence_actions:
        if "vacuum" in action:
            write_output(ModbusAddresses.CRANE_VACUUM, action["vacuum"])
            time.sleep(0.8 if action["vacuum"] == 0 else 0.5)

        if "setX" in action and "setY" in action:
            write_output(ModbusAddresses.CRANE_SET_X, action["setX"])
            write_output(ModbusAddresses.CRANE_SET_Y, action["setY"])
            wait_for_position(action["setX"], action["setY"])

        if "wait_for_process" in action:
            time.sleep(0.5)
            run_process1()

def run_process1():
    """Start Process1 and wait for completion"""
    print("  [PROCESS] Starting Process 1...")
    write_output(ModbusAddresses.PROCESS1_RUN, 1)
    time.sleep(1.0)

    # Wait for process to complete (check isRunning)
    start_time = time.time()
    while time.time() - start_time < 60:
        is_running = read_input(ModbusAddresses.PROCESS1_IS_RUNNING)
        if is_running == 0:
            print("  [PROCESS] Process 1 completed")
            # Turn off run signal
            write_output(ModbusAddresses.PROCESS1_RUN, 0)
            time.sleep(0.5)
            return True
        time.sleep(0.5)

    print("  [WARNING] Process 1 timeout")
    write_output(ModbusAddresses.PROCESS1_RUN, 0)
    return False

def process_part(part, sequences):
    """Process a single part through the system"""
    print(f"\n{'='*70}")
    print(f"[PROCESSING] Part #{part['id']} - Type {part['type']}")
    print(f"{'='*70}")

    # Step 1: Pick from Source1
    print(f"\n[Step 1] Picking part #{part['id']} from Source1")
    execute_sequence(sequences['pick_from_source1'])
    part['location'] = 'crane'
    part['status'] = 'in_transit'

    # Step 2: Place in Process1
    print(f"\n[Step 2] Placing part #{part['id']} in Process1")
    execute_sequence(sequences['place_in_process1'])
    part['location'] = 'process1'
    part['status'] = 'processing'

    # Step 3: Run Process1
    print(f"\n[Step 3] Running Process1 for part #{part['id']}")
    execute_sequence([sequences['run_process1']])

    # Step 4: Pick from Process1
    print(f"\n[Step 4] Picking processed part #{part['id']} from Process1")
    execute_sequence(sequences['pick_from_process1'])
    part['location'] = 'crane'
    part['status'] = 'in_transit'

    # Step 5: Place in Sink
    print(f"\n[Step 5] Delivering part #{part['id']} to Sink")
    execute_sequence(sequences['place_in_sink'])
    part['location'] = 'sink'
    part['status'] = 'completed'

    print(f"\n[COMPLETED] Part #{part['id']} delivered to Sink")

def load_sequences(filename):
    """Load sequences from JSON file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get("sequences", {})
    except Exception as e:
        print(f"Error loading sequences: {e}")
        return {}

def main():
    """Main function for Grade D"""
    print("="*70)
    print(" "*18 + "GRADE D: Crane Control with Queue")
    print(" "*15 + "Source1 → Process1 → Sink (Queue)")
    print("="*70)

    # Connect to Modbus
    print("\n[MODBUS] Connecting to 127.0.0.1...")
    if not client.connect():
        print("[ERROR] Failed to connect to Modbus server")
        return
    print("[MODBUS] Connected successfully")

    try:
        # Load sequences
        sequences = load_sequences("crane_sequence_d.json")
        if not sequences:
            print("[ERROR] Failed to load sequences")
            return

        print("\n[SYSTEM] Queue system initialized")
        print("[INFO] Click 'Generate' at Source1 to add parts to queue")
        print("[INFO] Press Ctrl+C to stop\n")

        # Initialize vacuum
        write_output(ModbusAddresses.CRANE_VACUUM, 0)

        last_check_time = time.time()

        while True:
            # Periodically check for new parts (every 0.5 seconds when idle)
            current_time = time.time()
            if current_time - last_check_time >= 0.5:
                check_for_new_parts()
                last_check_time = current_time

            # Process next part in queue if available
            if part_queue:
                part = part_queue.popleft()
                print(f"\n[QUEUE] Processing next part. Remaining in queue: {len(part_queue)}")

                process_part(part, sequences)

                # After processing, check again for new parts
                check_for_new_parts()
            else:
                # No parts in queue, wait for new parts
                print(f"\r[IDLE] Waiting for parts... (Queue: {len(part_queue)})", end='', flush=True)
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] System stopped by user")
        print(f"[SUMMARY] Parts remaining in queue: {len(part_queue)}")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[MODBUS] Closing connection...")
        client.close()
        print("[MODBUS] Connection closed")

if __name__ == "__main__":
    main()
