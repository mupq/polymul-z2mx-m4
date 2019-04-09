#!/usr/bin/env python3
import serial
import sys
import os
import subprocess
import hashlib
import datetime
import time
import numpy as np
dev = serial.Serial("/dev/ttyUSB0", 115200,timeout=10)

def benchmarkBinary(binary):
    print("Flashing {}..".format(binary))
    subprocess.run(["st-flash", "write", binary, "0x8000000"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Flashed, now running benchmarks..".format(binary))
    state = 'waiting'
    marker = b''
    # This parses test vector output starting with a number of leading '=',
    #  and expects a hashtag '#' after the test vector output.
    while True:
        x = dev.read()
        if x == b'' and state == 'waiting':
            print("timed out while waiting for the markers")
            return benchmarkBinary(binary)

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
    lines =b''.join(vector).decode("utf-8");
    lines = lines.split("\n");

    # sometimes the output markers end up as the first line of the output file
    if "=" in lines[0]:
        return [int(lines[2]), int(lines[5]), int(lines[8])];
    else:
        return [int(lines[1]), int(lines[4]), int(lines[7])];

def printStats(l):
    print("AVG: {:,}, MIN: {:,}, MAX: {:,}".format(int(np.mean(l)), min(l), max(l)))

def printResults(binary, data):
    print(f"#{binary}")
    print(data)
    keygen    = [item[0] for item in data]
    enc   = [item[1] for item in data]
    dec = [item[2] for item in data]
    print("keygen")
    printStats(keygen)
    print("enc")
    printStats(enc)
    print("dec")
    printStats(dec)

def doBenchmarks():
    binaries = ["benchmark-kindi256342.bin", "benchmark-ntruhrss701.bin"
                "benchmark-ntru-kem-743.bin", "benchmark-saber.bin",
                "benchmark-rlizard-1024-11.bin",
                "stack-kindi256342.bin", "stack-ntruhrss701.bin",
                "stack-ntru-kem-743.bin", "stack-saber.bin",
                "stack-rlizard-1024-11.bin"
                ]
    for binary in binaries:
        results = []
        subprocess.run(["make", binary],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for i in range(10):
            results.append(benchmarkBinary(binary))
            printResults(binary, results)
doBenchmarks()
