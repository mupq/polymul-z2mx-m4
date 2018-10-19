#!/usr/bin/env python3
import serial
import subprocess

dev = serial.Serial("/dev/ttyUSB0", 115200)

results = []
for i in range(1, 250):
    binary = f"benchmark-schoolbook_{i}.bin"
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
    vector = b''.join(vector).decode('utf-8').split("\n")
    n = 0
    for i in range(len(vector)):
        if vector[i] == "n: ":
            n = int(vector[i+1])
        if vector[i] == "cycles: ":
            cycles = int(vector[i+1])
            print("## found results")
        if vector[i] == "ERROR!":
            print("## FOUND AN ERROR!")
    results.append([n, cycles])
    print("| N | cycles ")
    for result in results:
        print(f"| {result[0]} | {result[1]}")

print("cleaning up...")
subprocess.run(["make", "clean"])
print("done...")
print("| N | cycles ")
for result in results:
    print(f"| {result[0]} | {result[1]}")
