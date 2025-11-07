"""
Grade B: Crane Control System with Both Part Types
Handles Type 1 (Source1) and Type 2 (Source2) parts with different sequences
Type 1: Source1 -> Process1 -> Sink
Type 2: Source2 -> Process2 -> Process1 -> Sink
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import time
import json
import csv
from datetime import datetime
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

# CSV logging
csv_filename = "crane_log.csv"
csv_file = None
csv_writer = None

def init_csv_logging():
    """Initialize CSV file for logging"""
    global csv_file, csv_writer
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['product_id', 'timestamp', 'x', 'y', 'vacuum'])
    csv_file.flush()
    print(f"[LOG] CSV logging initialized: {csv_filename}")

def log_position(product_id, x, y, vacuum):
    """Log current position to CSV"""
    global csv_writer, csv_file
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    csv_writer.writerow([product_id, timestamp, x, y, vacuum])
    csv_file.flush()

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
    """Check both sources for new parts and add to queue"""
    global part_id_counter

    # Check Source1 sensor
    source1_sensor = read_input(ModbusAddresses.SOURCE1_SENSOR)
    if source1_sensor == 1:
        if not any(p['location'] == 'source1' and p['status'] == 'waiting' for p in part_queue):
            part_id_counter += 1
            part = {
                'id': part_id_counter,
                'type': 1,
                'location': 'source1',
                'status': 'waiting'
            }
            part_queue.append(part)
            print(f"\n[QUEUE] New Type 1 part #{part['id']} detected at Source1")
            print(f"[QUEUE] Queue size: {len(part_queue)}")

    # Check Source2 sensor
    source2_sensor = read_input(ModbusAddresses.SOURCE2_SENSOR)
    if source2_sensor == 1:
        if not any(p['location'] == 'source2' and p['status'] == 'waiting' for p in part_queue):
            part_id_counter += 1
            part = {
                'id': part_id_counter,
                'type': 2,
                'location': 'source2',
                'status': 'waiting'
            }
            part_queue.append(part)
            print(f"\n[QUEUE] New Type 2 part #{part['id']} detected at Source2")
            print(f"[QUEUE] Queue size: {len(part_queue)}")

def execute_sequence(sequence_actions, part_id):
    """Execute a sequence of actions with logging"""
    for action in sequence_actions:
        if "vacuum" in action:
            vacuum_state = action["vacuum"]
            write_output(ModbusAddresses.CRANE_VACUUM, vacuum_state)
            time.sleep(0.8 if vacuum_state == 0 else 0.5)

        if "setX" in action and "setY" in action:
            target_x = action["setX"]
            target_y = action["setY"]
            write_output(ModbusAddresses.CRANE_SET_X, target_x)
            write_output(ModbusAddresses.CRANE_SET_Y, target_y)
            wait_for_position(target_x, target_y)

            # Log position after reaching target (if vacuum is active)
            vacuum = read_input(ModbusAddresses.CRANE_VACUUM)
            if vacuum == 1:  # Only log when holding a part
                pos_x = read_input(ModbusAddresses.CRANE_POS_X)
                pos_y = read_input(ModbusAddresses.CRANE_POS_Y)
                log_position(part_id, pos_x, pos_y, vacuum)

        if "wait_for_process" in action:
            time.sleep(0.5)
            process_num = action["wait_for_process"]
            if process_num == 1:
                run_process1()
            elif process_num == 2:
                run_process2()

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

def run_process2():
    """Start Process2 and wait for completion"""
    print("  [PROCESS] Starting Process 2...")
    write_output(ModbusAddresses.PROCESS2_RUN, 1)
    time.sleep(1.0)

    # Wait for process to complete (check isRunning)
    start_time = time.time()
    while time.time() - start_time < 60:
        is_running = read_input(ModbusAddresses.PROCESS2_IS_RUNNING)
        if is_running == 0:
            print("  [PROCESS] Process 2 completed")
            # Turn off run signal
            write_output(ModbusAddresses.PROCESS2_RUN, 0)
            time.sleep(0.5)
            return True
        time.sleep(0.5)

    print("  [WARNING] Process 2 timeout")
    write_output(ModbusAddresses.PROCESS2_RUN, 0)
    return False

def process_type1_part(part, sequences):
    """Process Type 1 part: Source1 -> Process1 -> Sink"""
    print(f"\n{'='*70}")
    print(f"[PROCESSING] Part #{part['id']} - Type 1 (Source1 -> Process1 -> Sink)")
    print(f"{'='*70}")

    # Pick from Source1
    print(f"\n[Step 1] Picking part #{part['id']} from Source1")
    execute_sequence(sequences['pick_from_source1'], part['id'])

    # Place in Process1
    print(f"\n[Step 2] Placing part #{part['id']} in Process1")
    execute_sequence(sequences['place_in_process1'], part['id'])

    # Run Process1
    print(f"\n[Step 3] Running Process1 for part #{part['id']}")
    execute_sequence([sequences['run_process1']], part['id'])

    # Pick from Process1
    print(f"\n[Step 4] Picking processed part #{part['id']} from Process1")
    execute_sequence(sequences['pick_from_process1'], part['id'])

    # Place in Sink
    print(f"\n[Step 5] Delivering part #{part['id']} to Sink")
    execute_sequence(sequences['place_in_sink'], part['id'])

    print(f"\n[COMPLETED] Part #{part['id']} delivered to Sink")

def process_type2_part(part, sequences):
    """Process Type 2 part: Source2 -> Process2 -> Process1 -> Sink"""
    print(f"\n{'='*70}")
    print(f"[PROCESSING] Part #{part['id']} - Type 2 (Source2 -> Process2 -> Process1 -> Sink)")
    print(f"{'='*70}")

    # Pick from Source2
    print(f"\n[Step 1] Picking part #{part['id']} from Source2")
    execute_sequence(sequences['pick_from_source2'], part['id'])

    # Place in Process2
    print(f"\n[Step 2] Placing part #{part['id']} in Process2")
    execute_sequence(sequences['place_in_process2'], part['id'])

    # Run Process2
    print(f"\n[Step 3] Running Process2 for part #{part['id']}")
    execute_sequence([sequences['run_process2']], part['id'])

    # Pick from Process2
    print(f"\n[Step 4] Picking part #{part['id']} from Process2")
    execute_sequence(sequences['pick_from_process2'], part['id'])

    # Place in Process1
    print(f"\n[Step 5] Placing part #{part['id']} in Process1")
    execute_sequence(sequences['place_in_process1'], part['id'])

    # Run Process1
    print(f"\n[Step 6] Running Process1 for part #{part['id']}")
    execute_sequence([sequences['run_process1']], part['id'])

    # Pick from Process1
    print(f"\n[Step 7] Picking part #{part['id']} from Process1")
    execute_sequence(sequences['pick_from_process1'], part['id'])

    # Place in Sink
    print(f"\n[Step 8] Delivering part #{part['id']} to Sink")
    execute_sequence(sequences['place_in_sink'], part['id'])

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
    """Main function for Grade B"""
    global csv_file

    print("="*70)
    print(" "*12 + "GRADE B: Crane Control with Both Part Types")
    print(" "*10 + "Type 1: Source1 → Process1 → Sink")
    print(" "*10 + "Type 2: Source2 → Process2 → Process1 → Sink")
    print("="*70)

    # Connect to Modbus
    print("\n[MODBUS] Connecting to 127.0.0.1...")
    if not client.connect():
        print("[ERROR] Failed to connect to Modbus server")
        return
    print("[MODBUS] Connected successfully")

    try:
        # Initialize CSV logging
        init_csv_logging()

        # Load sequences
        sequences = load_sequences("crane_sequence_b.json")
        if not sequences:
            print("[ERROR] Failed to load sequences")
            return

        print("\n[SYSTEM] Dual-queue system initialized")
        print("[INFO] Click 'Generate' at Source1 for Type 1 parts")
        print("[INFO] Click 'Generate' at Source2 for Type 2 parts")
        print("[INFO] Press Ctrl+C to stop\n")

        # Initialize vacuum
        write_output(ModbusAddresses.CRANE_VACUUM, 0)

        last_check_time = time.time()

        while True:
            # Periodically check for new parts
            current_time = time.time()
            if current_time - last_check_time >= 0.5:
                check_for_new_parts()
                last_check_time = current_time

            # Process next part in queue if available
            if part_queue:
                part = part_queue.popleft()
                print(f"\n[QUEUE] Processing next part. Remaining in queue: {len(part_queue)}")

                if part['type'] == 1:
                    process_type1_part(part, sequences)
                elif part['type'] == 2:
                    process_type2_part(part, sequences)

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
        if csv_file:
            csv_file.close()
            print(f"[LOG] CSV file closed: {csv_filename}")
        print("\n[MODBUS] Closing connection...")
        client.close()
        print("[MODBUS] Connection closed")

if __name__ == "__main__":
    main()
