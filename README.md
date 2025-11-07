# Crane Control System

**Grade A – E Modular Crane Automation System**  
A Python-based crane control system using **Modbus TCP** for communication with a simulated industrial environment. Supports **multiple part types**, **queue management**, **CSV logging**, and a **GUI/HMI** for manual control.

---

## Features by Grade

| Grade | Features |
|-------|---------|
| **E** | Single-part sequence: `Source1 → Process1 → Sink` |
| **D** | Queue system for multiple Type 1 parts |
| **C** | Queue + CSV logging of crane positions |
| **B** | Support for **Type 1** and **Type 2** parts with different processing paths |
| **A** | Full **GUI/HMI** with manual control, position saving, and sequence execution |

---

## System Overview
Source1 (Type 1) ──► [Crane] ──► Process1 ──► Sink
Source2 (Type 2) ──► [Crane] ──► Process2 ──► Process1 ──► Sink
text- **Type 1 Path**: `Source1 → Process1 → Sink`
- **Type 2 Path**: `Source2 → Process2 → Process1 → Sink`

---

## Project Structure
crane-control-system/
├── crane_control_a.py      # Grade A: Full GUI/HMI
├── crane_control_b.py      # Grade B: Dual part types + logging
├── crane_control_c.py      # Grade C: Queue + CSV logging
├── crane_control_d.py      # Grade D: Queue system (Type 1 only)
├── crane_control_e.py      # Grade E: Single part sequence
├── crane_sequence_a.json   # (Optional) Custom sequences for GUI
├── crane_sequence_b.json   # Sequences for Grade B
├── crane_sequence_c.json   # Sequences for Grade C
├── crane_sequence_d.json   # Sequences for Grade D
├── crane_sequence_e.json   # Full action list for Grade E
├── crane_log.csv           # Generated log (Grade C/B)
└── README.md
text---

## Requirements

- Python 3.6+
- `pymodbus`
- `tkinter` (included with Python)

Install dependencies:

```bash
pip install pymodbus

Usage
1. Start the Simulation
Ensure your Modbus TCP simulation is running on 127.0.0.1:502.

Example: Use ModbusPal or a custom simulator.

2. Run a Grade
bash# Grade E (Single Part)
python crane_control_e.py

# Grade D (Queue)
python crane_control_d.py

# Grade C (Queue + Logging)
python crane_control_c.py

# Grade B (Dual Parts + Logging)
python crane_control_b.py

# Grade A (Full GUI)
python crane_control_a.py
3. Generate Parts
In the simulation:

Click "Generate" on Source1 → Type 1 part
Click "Generate" on Source2 → Type 2 part


CSV Logging (Grade C & B)
Logs every position where the crane is holding a part:
csvproduct_id,timestamp,x,y,vacuum
1,2025-04-05T10:23:15,55,82,1
1,2025-04-05T10:23:18,450,82,1
...

GUI (Grade A)
<img src="https://via.placeholder.com/800x500.png?text=Crane+HMI+GUI+(Coming+Soon)" alt="GUI Preview">

Manual X/Y control
Predefined position buttons
Save/load custom positions
Execute JSON sequences
Real-time position & vacuum display


Modbus Register Map

Address,Function
1,CRANE_SET_X
2,CRANE_SET_Y
3,CRANE_VACUUM
4,PROCESS1_RUN
5,PROCESS2_RUN
15,CRANE_POS_X (input)
16,CRANE_POS_Y (input)
17,SOURCE1_SENSOR
18,SOURCE2_SENSOR
19,PROCESS1_IS_RUNNING
20,PROCESS2_IS_RUNNING
21,PROCESS1_SENSOR
22,PROCESS2_SENSOR

AddressFunction1CRANE_SET_X2CRANE_SET_Y3CRANE_VACUUM4PROCESS1_RUN5PROCESS2_RUN15CRANE_POS_X (input)16CRANE_POS_Y (input)17SOURCE1_SENSOR18SOURCE2_SENSOR19PROCESS1_IS_RUNNING20PROCESS2_IS_RUNNING21PROCESS1_SENSOR22PROCESS2_SENSOR

JSON Sequence Format
json{
  "sequences": {
    "pick_from_source1": [
      { "setX": 55, "setY": 200 },
      { "setX": 55, "setY": 82 },
      { "vacuum": 1 },
      { "setX": 55, "setY": 200 }
    ],
    "run_process1": { "wait_for_process": 1 }
  }
}

Contributing

Fork the repo
Create a feature branch
Commit changes
Push and open a Pull Request


License
MIT License

Built with industrial automation principles in mind
Modular | Scalable | Maintainable
text---

