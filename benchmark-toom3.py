#!/usr/bin/env python3
import serial
import subprocess
from math import ceil, floor

dev = serial.Serial("/dev/ttyUSB0", 115200)

results = []
for i in range(1, 1025):
    if ceil(i / 3) & 1:  # skip toom3 for n with odd limb sizes
        continue
    layers = 0
    while True:
        try:
            while True:
                t = ceil(ceil(i / 3) / (2 ** layers))
                if t < 6:
                    break
                if t > 48:
                    layers += 1
                    continue
                binary = f"benchmark-toom3_{i}_{t}.bin"
                print(f">>> making {binary}")
                subprocess.run(["make", binary])
                print("done")

                print(f">>> flashing {binary}")
                subprocess.run(["st-flash", "--reset", "write", binary, "0x8000000"])
                print("done")
                state = 'waiting'
                marker = b''
                while True:
                    x = dev.read()
                    if state == 'waiting':
                        if x == b'=':
                            marker += x
                            continue
                        # If we saw at least 5 equal signs, assume we've probably started
                        elif marker.count(b'=') > 5:
                            state = 'beginning'
                            vector = []
                            print("  .. found output marker..")
                    if state == 'beginning':
                        if x == b'=':
                            continue
                        else:
                            state = 'reading'
                    elif state == 'reading':
                        if x == b'#':
                            break
                        else:
                            vector.append(x)
                vector = b''.join(vector).decode('utf-8', errors='ignore').split("\n")
                for j in range(len(vector)):
                    if vector[j] == "n: ":
                        n = int(vector[j+1])
                    if vector[j] == "t: ":
                        t = int(vector[j+1])
                    if vector[j] == "cycles: ":
                        cycles = int(vector[j+1])
                        print("## found results")
                    if vector[j] == "ERROR!":
                        print("## FOUND AN ERROR!")

                results.append([n, t, cycles])
                print("| N | t | cycles ")
                for result in results:
                    print(f"| {result[0]} | {result[1]} | {result[2]} ")
                layers += 1
            break  # if we got here, we do not need to continue while True
        except:
            continue  # if any exception occurred, simply try this i again

print("cleaning up...")
subprocess.run(["make", "clean"])
print("done...")
