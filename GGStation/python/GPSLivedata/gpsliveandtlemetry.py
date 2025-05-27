# -*- coding: utf-8 -*-
"""
Telemetry Dashboard with Real GPS Data
@author: ashka
"""

import tkinter as tk
from PIL import Image, ImageTk
from math import sin, cos, radians
from collections import deque
from datetime import datetime
import time
import threading
import serial
import numpy as np
from scipy.signal import correlate, butter, filtfilt, welch
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkintermapview import TkinterMapView

# === MAIN WINDOW ===
root = tk.Tk()
root.title("🚀 Arbalest Rocketry - Telemetry Dashboard (Real GPS)")
root.configure(bg="#1e1e1e")
root.state("zoomed")

# === GRID CONFIG ===
for i in range(6):
    root.grid_rowconfigure(i, weight=1)
for j in range(4):
    root.grid_columnconfigure(j, weight=1)

# === LOGO ===
logo_img = Image.open("AB logo.png").resize((500, 120), Image.Resampling.LANCZOS)
logo_tk = ImageTk.PhotoImage(logo_img)
logo_label = tk.Label(root, image=logo_tk, bg="#1e1e1e")
logo_label.image = logo_tk
logo_label.grid(row=0, column=0, columnspan=4, pady=10, sticky="n")

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
fields = ["Yaw", "Pitch", "Roll", "Alt", "P", "T", "LED", "Lat", "Lon"]
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
labels["EVENT"] = tk.Label(event_frame, text="All nominal", font=("Helvetica", 11), fg="cyan", bg="#1e1e1e")
labels["EVENT"].pack(side="left")

# === GAUGES ===
gauge_frame = tk.Frame(root, bg="#1e1e1e")
gauge_frame.grid(row=1, column=1, rowspan=3, sticky="nsew", padx=10)
yaw_canvas = tk.Canvas(gauge_frame, width=150, height=150, bg="white")
pitch_canvas = tk.Canvas(gauge_frame, width=150, height=150, bg="white")
roll_canvas = tk.Canvas(gauge_frame, width=150, height=150, bg="white")
yaw_canvas.grid(row=0, column=0, padx=10, pady=5)
pitch_canvas.grid(row=0, column=1, padx=10, pady=5)
roll_canvas.grid(row=0, column=2, padx=10, pady=5)

def draw_gauge(canvas, angle, label):
    canvas.delete("all")
    cx, cy, r = 75, 75, 60
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="black", width=2)
    canvas.create_text(cx, 10, text=label, font=("Arial", 12, "bold"))
    x = cx + r * 0.8 * cos(radians(angle - 90))
    y = cy + r * 0.8 * sin(radians(angle - 90))
    canvas.create_line(cx, cy, x, y, fill="red", width=3)
    canvas.create_text(cx, cy + r + 10, text=f"{angle:.1f}°", font=("Arial", 10))

# === TELEMETRY PLOTS ===
telemetry_data = {k: deque(maxlen=100) for k in ["time", "Alt", "P", "T", "Lat", "Lon"]}
plot_fields = ["Alt", "P", "T", "Lat", "Lon"]
figs, axes, plots = [], [], []
plot_frame = tk.Frame(root, bg="#1e1e1e")
plot_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
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

# === MAP ===
map_frame = tk.Frame(root)
map_frame.grid(row=1, column=2, rowspan=4, sticky="nsew", padx=10, pady=10)
map_widget = TkinterMapView(map_frame, width=400, height=400, corner_radius=10)
map_widget.pack(fill="both", expand=True)
map_widget.set_position(43.7735, -79.5015)
map_marker = map_widget.set_marker(43.7735, -79.5015, text="Rocket")

def update_gps_data(lat, lon):
    now = time.time() - start_time
    telemetry_data["time"].append(now)
    telemetry_data["Lat"].append(lat)
    telemetry_data["Lon"].append(lon)

    labels["Lat"].config(text=f"{lat:.5f}")
    labels["Lon"].config(text=f"{lon:.5f}")

    map_marker.set_position(lat, lon)
    map_widget.set_position(lat, lon)

    update_plots()

# === REAL GPS SERIAL ===
def extract_lat_lon(line):
    try:
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "GPS:":
            lat = float(parts[1])
            lon = float(parts[2])
            return lat, lon
    except:
        return None, None
    return None, None

def read_gps_serial():
    try:
        ser = serial.Serial("COM7", 9600, timeout=1)
        print("Reading GPS data from COM7...")
    except Exception as e:
        print(f"Failed to open serial: {e}")
        return

    while True:
        try:
            line = ser.readline().decode('ascii', errors='replace').strip()
            print("GPS:", line)
            lat, lon = extract_lat_lon(line)
            if lat and lon:
                update_gps_data(lat, lon)
        except Exception as e:
            print("Serial read error:", e)
            continue

# === ADVANCED ANALYSIS ===
def plot_psd(field):
    data = np.array(telemetry_data[field])
    times = np.array(telemetry_data["time"])
    if len(data) < 10:
        return
    fs = 1 / (np.mean(np.diff(times)))
    f, Pxx = welch(data, fs=fs, nperseg=min(256, len(data)))
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.semilogy(f, Pxx, color='lime')
    ax.set_title(f"PSD of {field}", fontsize=10)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Power")
    ax.grid(True)
    plt.tight_layout()
    plt.show()

def plot_cross_corr(x_key, y_key):
    x = np.array(telemetry_data[x_key])
    y = np.array(telemetry_data[y_key])
    if len(x) < 10 or len(y) < 10:
        return
    corr = correlate(x - np.mean(x), y - np.mean(y), mode='full')
    lags = np.arange(-len(x)+1, len(x))
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(lags, corr, color='orange')
    ax.set_title(f"Cross-Correlation: {x_key} vs {y_key}", fontsize=10)
    ax.set_xlabel("Lag")
    ax.set_ylabel("Correlation")
    plt.tight_layout()
    plt.show()

def low_pass_filter(data, fs, cutoff=0.2):
    nyq = 0.5 * fs
    norm_cutoff = cutoff / nyq
    b, a = butter(2, norm_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def plot_filtered_altitude():
    data = np.array(telemetry_data["Alt"])
    times = np.array(telemetry_data["time"])
    if len(data) < 10:
        return
    fs = 1 / (np.mean(np.diff(times)))
    filtered = low_pass_filter(data, fs)
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(times, data, label="Raw", alpha=0.5)
    ax.plot(times, filtered, label="Filtered", color='magenta')
    ax.set_title("Altitude: Raw vs Filtered", fontsize=10)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Altitude")
    ax.legend()
    plt.tight_layout()
    plt.show()

# === BUTTONS ===
analysis_frame = tk.Frame(root, bg="#1e1e1e")
analysis_frame.grid(row=5, column=0, columnspan=2, pady=10)
tk.Label(analysis_frame, text="Telemetry Analysis", font=("Helvetica", 12, "bold"), fg="white", bg="#1e1e1e").pack()
tk.Button(analysis_frame, text="Plot PSD (Altitude)", command=lambda: plot_psd("Alt")).pack(side="left", padx=5)
tk.Button(analysis_frame, text="Plot PSD (Pressure)", command=lambda: plot_psd("P")).pack(side="left", padx=5)
tk.Button(analysis_frame, text="Pitch vs Roll Corr", command=lambda: plot_cross_corr("Pitch", "Roll")).pack(side="left", padx=5)
tk.Button(analysis_frame, text="Filter Altitude", command=plot_filtered_altitude).pack(side="left", padx=5)

# === START ===
start_time = time.time()
gps_thread = threading.Thread(target=read_gps_serial, daemon=True)
gps_thread.start()
root.mainloop()
