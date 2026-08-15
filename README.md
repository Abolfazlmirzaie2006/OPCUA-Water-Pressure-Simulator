# OPC UA Water Pressure Simulator

Python GUI simulator for a city water pressure network. Uses OPC UA to communicate seamlessly with Siemens physical PLCs or PLCSIM Advanced.

This project allows automation engineers to test, tune, and validate PID control loops for pump stations without requiring physical hardware, acting as a real-time virtual plant.

## 📌 Features
* **OPC UA Connectivity:** Direct communication with Siemens S7 PLCs. Includes manual connect/disconnect controls via the GUI.
* **Real-time Physics Engine:** Calculates pressure dynamics based on pump input flow, network capacity, and variable consumer demand.
* **Dual Operating Modes:**
  * **Manual Mode:** Manually adjust 10 individual consumer valves (0-100%) to simulate specific load disturbances.
  * **Automatic Mode:** Runs a dynamic 6-minute simulation cycle mimicking real-world city water consumption (increasing demand, decreasing demand, and low-demand night phases).
* **Interactive GUI:** Real-time visualization of system pressure, PID output, and cycle status using Tkinter.

---

## ⚙️ TIA Portal Configuration (Step-by-Step Guide)

This guide is optimized for Siemens TIA Portal V21 and PLCSIM Advanced V8.0, but the core steps apply to earlier versions (S7-1200 / S7-1500) as well.

### Step 1: Enable the OPC UA Server
1. Open your TIA Portal project and go to **Device Configuration**.
2. Click on your CPU.
3. In the Inspector window (Properties tab), navigate to **OPC UA** > **Server** > **General**.
4. Check the box **"Activate OPC UA server"**.
5. Note the Server Address (typically `opc.tcp://192.168.0.1:4840`). If you are using PLCSIM Advanced V8.0, ensure your virtual Ethernet adapter is correctly routed and active.
6. Under **Runtime licenses**, ensure the OPC UA license is set to the correct level for your CPU.

### Step 2: Create the Data Block (DB)
1. In the Project tree on the left, navigate to **Program blocks** -> double-click **Add new block**.
2. Select **Data block (DB)**.
3. Choose **Global DB**.
4. Name the block exactly: `PID_OPCUA_DB1` (The Python script looks for this exact name).
5. Click **OK**.

### Step 3: Define the Variables
Inside the newly created `PID_OPCUA_DB1`, add the following three variables exactly as written:

| Name | Data Type | Description |
| :--- | :--- | :--- |
| `output` | `Real` | The control signal (0-100%) coming from your PLC's PID block to control the virtual pump. |
| `Feedback` | `Real` | The current system pressure (Bar) calculated and sent by the Python simulator. |
| `Setpoint` | `Real` | The target pressure (Bar) sent from the Python GUI to the PLC. |

### Step 4: Configure OPC UA Accessibility
1. Still inside `PID_OPCUA_DB1`, look at the columns on the right side of the variable table.
2. Ensure the checkboxes for **"Accessible from HMI/OPC UA"** and **"Writable from HMI/OPC UA"** are checked (True) for all three variables.
3. *Important:* Right-click `PID_OPCUA_DB1` in the project tree, go to **Properties**, and ensure **"Optimized block access"** is checked (this is usually the default for S7-1200/1500).

### Step 5: Connect to the PID Controller
In your Main OB or cyclic interrupt (e.g., OB30):
* Assign `PID_OPCUA_DB1.Feedback` to the **Input** of your `PID_Compact` block.
* Assign `PID_OPCUA_DB1.Setpoint` to the **Setpoint** of your `PID_Compact` block.
* Assign the output of your `PID_Compact` block to `PID_OPCUA_DB1.output`.

Compile your software and hardware configurations, and download them to your physical PLC or PLCSIM Advanced instance.

---

## 🛠️ Python Environment Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Abolfazlmirzaie2006/OPCUA-Water-Pressure-Simulator.git](https://github.com/Abolfazlmirzaie2006/OPCUA-Water-Pressure-Simulator.git)
   ```

2. **Install requirements:**
   Ensure you have Python installed, then install the Asyncua library:
   ```bash
   pip install asyncua
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

4. Click **Connect PLC** in the GUI to start communicating with TIA Portal!

## 📝 License
This project is open-source and available under the MIT License.
