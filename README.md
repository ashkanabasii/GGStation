# GGStation
Ground Station 3D visualization 
# -*- coding: utf-8 -*-
"""
Created on Fri May 27 22:12:00 2025
@author: ashka
"""
from vpython import *
import serial
import math
import numpy as np
import re
from time import sleep

# === Serial Setup ===
ad = serial.Serial('COM6', 115200)  # Change COM port if needed
sleep(1)

# === Scene Setup ===
scene.range = 5
scene.background = color.black
scene.forward = vector(-1, -1, -1)
scene.width = 1200
scene.height = 1080
scene.title = "🚀 Real-Time Rocket Orientation (LoRa RF)"

# === Static Reference Arrows
xarrow = arrow(length=2, shaftwidth=0.1, color=color.red, axis=vector(1, 0, 0))
yarrow = arrow(length=2, shaftwidth=0.1, color=color.green, axis=vector(0, 1, 0))
zarrow = arrow(length=4, shaftwidth=0.1, color=color.blue, axis=vector(0, 0, 1))

# === Dynamic Orientation Arrows
frontArrow = arrow(length=4, shaftwidth=0.1, color=color.purple)
upArrow = arrow(length=1, shaftwidth=0.1, color=color.magenta)
sideArrow = arrow(length=2, shaftwidth=0.1, color=color.orange)

# === 3D Model: Two-Stage Rocket ===
stage1 = cylinder(radius=0.5, length=4, color=color.red, axis=vector(0, 1, 0), pos=vector(0, 0, 0))
stage2 = cylinder(radius=0.4, length=3, color=color.white, axis=vector(0, 1, 0), pos=vector(0, 4, 0))
nose = cone(radius=0.4, length=1, color=color.gray(0.5), axis=vector(0, 1, 0), pos=vector(0, 7, 0))
fin1 = box(length=0.1, height=1, width=1, color=color.white, pos=vector(0.5, -0.5, 0))
fin2 = box(length=0.1, height=1, width=1, color=color.white, pos=vector(-0.5, -0.5, 0))
fin3 = box(length=1, height=1, width=0.1, color=color.white, pos=vector(0, -0.5, 0.5))
fin4 = box(length=1, height=1, width=0.1, color=color.white, pos=vector(0, -0.5, -0.5))
myObj = compound([stage1, stage2, nose, fin1, fin2, fin3, fin4])

# === Main Loop
while True:
    rate(60)
    try:
        while ad.in_waiting:
            last_line = ad.readline()
        data = last_line.decode('utf-8', errors='ignore').strip()
        # print("Raw:", data)

        # Use regex to extract quaternion values robustly
        match = re.search(r"qw[: ]\s*(-?[\d.]+)[, ]+qx[: ]\s*(-?[\d.]+)[, ]+qy[: ]\s*(-?[\d.]+)[, ]+qz[: ]\s*(-?[\d.]+)", data)
        if not match:
            continue

        q0 = float(match.group(1))
        q1 = float(match.group(2))
        q2 = float(match.group(3))
        q3 = float(match.group(4))

        # Normalize quaternion
        norm = math.sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3)
        if norm == 0:
            continue
        q0, q1, q2, q3 = q0 / norm, q1 / norm, q2 / norm, q3 / norm

        # Compute orientation
        roll = -math.atan2(2*(q0*q1 + q2*q3), 1 - 2*(q1*q1 + q2*q2))
        pitch = math.asin(2*(q0*q2 - q3*q1))
        yaw = -math.atan2(2*(q0*q3 + q1*q2), 1 - 2*(q2*q2 + q3*q3)) - np.pi/2

        k = vector(math.cos(yaw)*math.cos(pitch), math.sin(pitch), math.sin(yaw)*math.cos(pitch))
        y_ref = vector(0, 1, 0)
        s = cross(k, y_ref)
        v = cross(s, k)
        vrot = v * math.cos(roll) + cross(k, v) * math.sin(roll)

        # Apply to model
        frontArrow.axis = k
        sideArrow.axis = cross(k, vrot)
        upArrow.axis = vrot
        myObj.axis = k
        myObj.up = vrot

    except Exception as e:
        print(f"⚠️ Error: {e}")
