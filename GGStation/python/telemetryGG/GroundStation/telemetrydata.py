import serial
import tkinter as tk
from PIL import Image, ImageTk
import sys
from math import sin, cos, radians
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from datetime import datetime
import time

# === SERIAL CONFIG ===
SERIAL_PORT = 'COM14'  # Replace with your actual port
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except Exception as e:
    print(f"❌ Could not open {SERIAL_PORT}: {e}")
    sys.exit()

root = tk.Tk()
root.title("🚀 Arbalest Rocketry - Telemetry Dashboard")
root.configure(bg="#1e1e1e")
root.state("zoomed")  # Start maximized

# === Grid Scaling for Resizability ===
for i in range(6):  # rows
    root.grid_rowconfigure(i, weight=1)
for j in range(3):  # columns
    root.grid_columnconfigure(j, weight=1)

# === LOGO ===
logo_img = Image.open("AB logo.png").resize((500, 120), Image.Resampling.LANCZOS)
logo_tk = ImageTk.PhotoImage(logo_img)
logo_label = tk.Label(root, bg="#1e1e1e")
logo_label.image = logo_tk
logo_label.config(image=logo_tk)
logo_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="n")

# === CLOCK ===
def update_clock():
    utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    lst = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    utc_label.config(text=f"UTC: {utc}")
    lst_label.config(text=f"LST: {lst}")
    root.after(1000, update_clock)

clock_frame = tk.Frame(root, bg="#1e1e1e")
clock_frame.grid(row=1, column=0, sticky="nw", padx=20)
utc_label = tk.Label(clock_frame, text="", font=("Consolas", 10), fg="white", bg="#1e1e1e")
lst_label = tk.Label(clock_frame, text="", font=("Consolas", 10), fg="white", bg="#1e1e1e")
utc_label.pack(anchor="w")
lst_label.pack(anchor="w")
update_clock()

# === TELEMETRY LABELS ===
labels = {}
# fields = ["Yaw", "Pitch", "Roll", "Alt", "P", "T", "LED"]
fields = ["Yaw", "Pitch", "Roll", "Alt", "P", "Stage", "LED"]
telemetry_frame = tk.Frame(root, bg="#1e1e1e")
telemetry_frame.grid(row=2, column=0, sticky="nw", padx=20)

for field in fields:
    row = tk.Frame(telemetry_frame, bg="#1e1e1e")
    row.pack(anchor="w")
    tk.Label(row, text=f"{field}:", font=("Helvetica", 11, "bold"), fg="white", bg="#1e1e1e", width=5).pack(side="left")
    labels[field] = tk.Label(row, text="---", font=("Helvetica", 11), fg="cyan", bg="#1e1e1e")
    labels[field].pack(side="left")

# === EVENT ===
event_frame = tk.Frame(root, bg="#1e1e1e")
event_frame.grid(row=3, column=0, sticky="w", padx=20, pady=5)
tk.Label(event_frame, text="EVENT:", font=("Helvetica", 11, "bold"), fg="white", bg="#1e1e1e").pack(side="left")
labels["EVENT"] = tk.Label(event_frame, text="---", font=("Helvetica", 11), fg="cyan", bg="#1e1e1e")
labels["EVENT"].pack(side="left")

# === GAUGES ===
gauge_frame = tk.Frame(root, bg="#1e1e1e")
gauge_frame.grid(row=1, column=1, rowspan=3, sticky="nsew", padx=20)

yaw_canvas = tk.Canvas(gauge_frame, width=150, height=150, bg="white")
pitch_canvas = tk.Canvas(gauge_frame, width=150, height=150, bg="white")
roll_canvas = tk.Canvas(gauge_frame, width=150, height=150, bg="white")
yaw_canvas.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
pitch_canvas.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
roll_canvas.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")

def draw_gauge(canvas, angle, label):
    canvas.delete("all")
    cx, cy, r = 75, 75, 60
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="black", width=2)
    canvas.create_text(cx, 10, text=label, font=("Arial", 12, "bold"))
    x = cx + r * 0.8 * cos(radians(angle - 90))
    y = cy + r * 0.8 * sin(radians(angle - 90))
    canvas.create_line(cx, cy, x, y, fill="red", width=3)
    canvas.create_text(cx, cy + r + 10, text=f"{angle:.1f}°", font=("Arial", 10))

# === PLOTS ===
#telemetry_data = {k: deque(maxlen=100) for k in ["time", "Alt", "P", "T", "Lat", "Lon"]}
telemetry_data = {k: deque(maxlen=100) for k in ["time", "Alt", "P"]}
# plot_fields = ["Alt", "P", "T", "Lat", "Lon"]

plot_fields = ["Alt", "P"]
figs, axes, plots = [], [], []

plot_frame = tk.Frame(root, bg="#1e1e1e")
plot_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

for i, field in enumerate(plot_fields):
    plot_frame.grid_rowconfigure(i // 2, weight=1)
    plot_frame.grid_columnconfigure(i % 2, weight=1)

    fig, ax = plt.subplots(figsize=(3, 1.5))
    fig.patch.set_facecolor('#1e1e1e')
    ax.set_facecolor('#2e2e2e')
    ax.tick_params(colors='white')
    ax.set_title(f"{field} vs Time", color='white', fontsize=8)
    ax.set_xlabel("Time (s)", color='white', fontsize=6)
    ax.set_ylabel(field, color='white', fontsize=6)
    line, = ax.plot([], [], color='cyan', linewidth=1)

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.get_tk_widget().grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="nsew")
    figs.append(fig)
    axes.append(ax)
    plots.append((line, canvas))

# === ALTITUDE BASELINE ===
baseline_altitude = None

# === PARSER ===
# def parse_telemetry(line):
#    global baseline_altitude
#    if "EVENT" in line:
#        labels["EVENT"].config(text=line.replace("Received: ", ""))
#        return
#    if "Yaw:" in line:
#        try:
#            now = time.time()
#            data = line.replace("Received: ", "").split(", ")
#            yaw = pitch = roll = 0
#            for d in data:
#                if ": " in d:
#                    key, val = d.split(": ")
#                    val = val.strip().replace("m", "").replace("Pa", "").replace("C", "")
#                    if key in labels:
#                        labels[key].config(text=val)
#                    if key in telemetry_data:
#                        if key == "Alt":
#                            raw_alt = float(val)
#                            if baseline_altitude is None:
#                                baseline_altitude = raw_alt
#                            alt = raw_alt - baseline_altitude
#                           telemetry_data["Alt"].append(alt)
#                          telemetry_data["time"].append(now)
#                        else:
#                           telemetry_data[key].append(float(val))
#                    if key == "Yaw": yaw = float(val)
#                    if key == "Pitch": pitch = float(val)
#                    if key == "Roll": roll = float(val)
#            draw_gauge(yaw_canvas, yaw % 360, "Yaw")
#            draw_gauge(pitch_canvas, pitch, "Pitch")
#            draw_gauge(roll_canvas, roll, "Roll")
#            update_plots()
#        except Exception as e:
#            print("Parse error:", e)

def parse_telemetry(line):
    global baseline_altitude
    if "Received:" in line and "Stage:" in line:
        try:
            now = time.time()
            data = line.replace("Received: ", "").split(", ")
            yaw = pitch = roll = stage = 0.0
            for d in data:
                if ": " in d:
                    key, val = d.split(": ")
                    val = val.strip()
                    if key == "Filt_Alt":
                        alt = float(val)
                        if baseline_altitude is None:
                            baseline_altitude = alt
                        rel_alt = alt - baseline_altitude
                        labels["Alt"].config(text=f"{rel_alt:.2f}")
                        telemetry_data["Alt"].append(rel_alt)
                        telemetry_data["time"].append(now)
                    elif key == "Filt_Acc":
                        acc = float(val)
                        labels["P"].config(text=f"{acc:.2f}")
                        telemetry_data["P"].append(acc)
                    elif key == "AngleX":
                        yaw = float(val)
                        labels["Yaw"].config(text=f"{yaw:.2f}")
                    elif key == "AngleY":
                        pitch = float(val)
                        labels["Pitch"].config(text=f"{pitch:.2f}")
                    elif key == "Stage":
                        stage = int(val)
                        labels["Stage"].config(text=f"{stage}")
                        labels["EVENT"].config(text=f"Stage {stage}")
            draw_gauge(yaw_canvas, yaw % 360, "Yaw")
            draw_gauge(pitch_canvas, pitch, "Pitch")
            draw_gauge(roll_canvas, roll, "Roll")
            update_plots()
        except Exception as e:
            print("Parse error:", e)



# === PLOT UPDATER ===
def update_plots():
    times = telemetry_data["time"]
    for i, field in enumerate(plot_fields):
        line, canvas = plots[i]
        y = telemetry_data[field]
        if len(times) == len(y):
            line.set_data(times, y)
            axes[i].relim()
            axes[i].autoscale_view()
            canvas.draw()

# === SERIAL READER ===
def read_serial():
    try:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                parse_telemetry(line)
    except Exception as e:
        print("Serial read error:", e)
    root.after(10, read_serial)

root.after(10, read_serial)
root.mainloop()
