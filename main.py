import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from asyncua import Client, ua
import random
import math
import time
import os

# --- OPC UA Configuration ---
URL = "opc.tcp://192.168.0.1:4840"
NODE_PUMP = 'ns=3;s="PID_OPCUA_DB1"."output"'
NODE_FEEDBACK = 'ns=3;s="PID_OPCUA_DB1"."Feedback"'
NODE_SETPOINT = 'ns=3;s="PID_OPCUA_DB1"."Setpoint"'

class PressureSystem:
    def __init__(self):
        self.pressure = 0.0          # Load (0 to 20 Bar)
        self.pump_speed = 0.0        # Percent (0 to 100%)
        self.valves = [0.0] * 10     # 10 Valves (0 to 100%)
        self.mode = "MANUAL"         # MANUAL or AUTO
        self.connected = False
        self.connect_requested = False
        self.new_setpoint = None
        self.start_time = time.time() 
        self.cycle_status = "Manual Mode"

    def update_physics(self, dt=0.5):
        # 1. Input flow from the pump
        flow_in = (self.pump_speed / 100.0) * 100.0 
        
        # 2. Output flow to consumers
        total_valve_area = sum(self.valves) / 1000.0
        flow_out = (total_valve_area * 15.0 + 0.5) * math.sqrt(max(0.01, self.pressure))
        
        # 3. Pressure changes based on network capacity
        capacity = 15.0 
        dp = (flow_in - flow_out) / capacity * dt
        
        self.pressure += dp
        
        # Limit pressure between 0 and 20 Bar
        self.pressure = max(0.0, min(20.0, self.pressure))

    def apply_auto_consumption(self):
        if self.mode == "AUTO":
            # 360-second (6 minutes) cycle simulation
            # 0-120s: Increasing | 120-240s: Decreasing | 240-360s: Stable Low
            t = (time.time() - self.start_time) % 360.0

            if t < 120.0:
                self.cycle_status = f"Phase 1: Increasing Demand ({(120-t):.0f}s left)"
                base_open = 10.0 + (80.0 * (t / 120.0))
            elif t < 240.0:
                self.cycle_status = f"Phase 2: Decreasing Demand ({(240-t):.0f}s left)"
                base_open = 90.0 - (80.0 * ((t - 120.0) / 120.0))
            else:
                self.cycle_status = f"Phase 3: Low Demand/Night ({(360-t):.0f}s left)"
                base_open = 10.0

            # Apply calculated values to valves with natural noise
            for i in range(10):
                noise = random.uniform(-3.0, 3.0)
                target = max(0.0, min(100.0, base_open + noise))
                # Low-pass filter for smooth valve transitions
                self.valves[i] += (target - self.valves[i]) * 0.1
        else:
            self.cycle_status = "Manual Mode - Custom Values"
            # Reset start time so cycle restarts when switched back to AUTO
            self.start_time = time.time() 

system = PressureSystem()

async def opcua_task():
    client = Client(url=URL)
    node_pump = None
    node_feedback = None
    node_setpoint = None

    while True:
        # Handle connection
        if system.connect_requested and not system.connected:
            print(f"Connecting to {URL} ...")
            try:
                await client.connect()
                print("OPC UA Connected Successfully!")
                system.connected = True
                
                node_pump = client.get_node(NODE_PUMP)
                node_feedback = client.get_node(NODE_FEEDBACK)
                node_setpoint = client.get_node(NODE_SETPOINT)
            except Exception as e:
                print(f"OPC UA Connection Error: {e}")
                system.connected = False
                system.connect_requested = False

        # Handle disconnection
        elif not system.connect_requested and system.connected:
            print("Disconnecting from PLC...")
            try:
                await client.disconnect()
                print("OPC UA Disconnected Successfully!")
            except Exception as e:
                print(f"OPC UA Disconnect Error: {e}")
            finally:
                system.connected = False

        # Main communication and simulation loop
        if system.connected:
            try:
                if system.new_setpoint is not None:
                    await node_setpoint.write_value(ua.DataValue(ua.Variant(float(system.new_setpoint), ua.VariantType.Float)))
                    system.new_setpoint = None

                system.pump_speed = await node_pump.read_value()
                
                system.update_physics(dt=0.5)
                system.apply_auto_consumption()

                clean_pressure = round(system.pressure, 3)
                await node_feedback.write_value(ua.DataValue(ua.Variant(float(clean_pressure), ua.VariantType.Float)))
            except Exception as e:
                print(f"OPC UA Communication Error: {e}")
                system.connected = False
        else:
            # Run simulation locally even when PLC is disconnected
            system.update_physics(dt=0.5)
            system.apply_auto_consumption()

        await asyncio.sleep(0.5)

def start_opc_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(opcua_task())

# ==========================================
# GUI Application
# ==========================================
def update_gui():
    if system.connected:
        lbl_status.config(text="Status: Connected to PLC", fg="#27ae60")
    else:
        if system.connect_requested:
            lbl_status.config(text="Status: Connecting...", fg="#f39c12")
        else:
            lbl_status.config(text="Status: Disconnected", fg="#c0392b")
        
    lbl_pressure.config(text=f"System Pressure: {system.pressure:.2f} Bar")
    lbl_pump.config(text=f"Pump Command (PID): {system.pump_speed:.1f} %")
    lbl_cycle.config(text=system.cycle_status) 
    
    if system.mode == "AUTO":
        for i, var in enumerate(valve_vars):
            var.set(system.valves[i])
            
    root.after(500, update_gui)

def set_mode(m):
    system.mode = m
    if m == "AUTO":
        btn_auto.config(bg="#3498db", fg="white", relief="sunken")
        btn_manual.config(bg="SystemButtonFace", fg="black", relief="raised")
        for slider in sliders:
            slider.config(state="disabled")
    else:
        btn_manual.config(bg="#3498db", fg="white", relief="sunken")
        btn_auto.config(bg="SystemButtonFace", fg="black", relief="raised")
        for slider in sliders:
            slider.config(state="normal")

def request_connect():
    system.connect_requested = True

def request_disconnect():
    system.connect_requested = False

def on_slider_change(event, index):
    if system.mode == "MANUAL":
        system.valves[index] = valve_vars[index].get()

def apply_sp():
    try:
        val = float(entry_sp.get())
        if 0 <= val <= 20: 
            system.new_setpoint = val
        else:
            messagebox.showerror("Error", "Pressure must be between 0 and 20 Bar.")
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid numeric value.")

def on_close():
    root.destroy()
    os._exit(0)

# Main Window Setup
root = tk.Tk()
root.title("Water Supply Network Simulator - Pressure Control")
root.geometry("600x750")
root.protocol("WM_DELETE_WINDOW", on_close)

# Top Header Frame
frame_top = tk.Frame(root, bg="#2c3e50", pady=15)
frame_top.pack(fill="x")

lbl_status = tk.Label(frame_top, text="Status: Starting...", font=("Arial", 12, "bold"), bg="#2c3e50", fg="white")
lbl_status.pack()

# Connection Control Buttons
frame_conn = tk.Frame(frame_top, bg="#2c3e50")
frame_conn.pack(pady=5)
tk.Button(frame_conn, text="Connect PLC", command=request_connect, font=("Arial", 9, "bold"), bg="#27ae60", fg="white", width=15).pack(side="left", padx=5)
tk.Button(frame_conn, text="Disconnect PLC", command=request_disconnect, font=("Arial", 9, "bold"), bg="#e74c3c", fg="white", width=15).pack(side="left", padx=5)

lbl_pressure = tk.Label(frame_top, text="System Pressure: 0.00 Bar", font=("Arial", 22, "bold"), bg="#2c3e50", fg="#00ffcc")
lbl_pressure.pack(pady=5)

lbl_pump = tk.Label(frame_top, text="Pump Command (PID): 0.0 %", font=("Arial", 14), bg="#2c3e50", fg="#f1c40f")
lbl_pump.pack()

lbl_cycle = tk.Label(frame_top, text="Manual Mode", font=("Arial", 12, "italic"), bg="#2c3e50", fg="#ecf0f1")
lbl_cycle.pack(pady=5)

# Setpoint Frame
frame_sp = tk.Frame(root, pady=15)
frame_sp.pack(fill="x")
tk.Label(frame_sp, text="Pressure Setpoint (0-20 Bar):", font=("Arial", 12)).pack(side="left", padx=20)
entry_sp = tk.Entry(frame_sp, font=("Arial", 14), width=8, justify="center")
entry_sp.insert(0, "8.0")
entry_sp.pack(side="left")
tk.Button(frame_sp, text="Apply to PLC", command=apply_sp, font=("Arial", 10, "bold"), bg="#27ae60", fg="white").pack(side="left", padx=20)

tk.Frame(root, height=2, bg="lightgrey").pack(fill="x", pady=5)

# Mode Selection Frame
frame_mode = tk.Frame(root, pady=10)
frame_mode.pack()
tk.Label(frame_mode, text="Consumption Mode:", font=("Arial", 12, "bold")).pack(side="left", padx=10)
btn_auto = tk.Button(frame_mode, text="AUTOMATIC (City Network)", font=("Arial", 10, "bold"), width=20, command=lambda: set_mode("AUTO"))
btn_auto.pack(side="left", padx=5)
btn_manual = tk.Button(frame_mode, text="MANUAL (Custom)", font=("Arial", 10, "bold"), width=20, command=lambda: set_mode("MANUAL"))
btn_manual.pack(side="left", padx=5)

tk.Frame(root, height=2, bg="lightgrey").pack(fill="x", pady=5)

# Valves (Consumers) Frame
tk.Label(root, text="Consumers (10 Variable Valves - %)", font=("Arial", 14, "bold"), fg="#2980b9").pack(pady=10)

frame_valves = tk.Frame(root)
frame_valves.pack(fill="both", expand=True, padx=20)

valve_vars = []
sliders = []

for i in range(10):
    row = i // 2
    col = i % 2
    vf = tk.Frame(frame_valves, pady=12, padx=15)
    vf.grid(row=row, column=col, sticky="ew")
    
    tk.Label(vf, text=f"Valve {i+1}", font=("Arial", 11, "bold")).pack(side="left")
    var = tk.DoubleVar()
    valve_vars.append(var)
    
    slider = ttk.Scale(vf, from_=0, to=100, variable=var, orient="horizontal", length=160,
                       command=lambda val, idx=i: on_slider_change(val, idx))
    slider.pack(side="right")
    sliders.append(slider)

set_mode("MANUAL")

# Start OPC UA Thread and GUI Update Loop
threading.Thread(target=start_opc_thread, daemon=True).start()
root.after(500, update_gui)
root.mainloop()
