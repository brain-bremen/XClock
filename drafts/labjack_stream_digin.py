import labjack.ljm as ljm
from xclock.devices import LabJackT4
from xclock.devices.labjack_devices import ClockRegisters, DigIoRegisters
import csv
from datetime import datetime
import numpy as np
import sys
import matplotlib.pyplot as plt

# Open LabJack T4
t4 = LabJackT4()

t4.add_clock_channel(100, "DIO6")
t4.add_clock_channel(30, "DIO7")
t4.start_clocks()


# Define streaming parameters
channel_names = ["DIO4", "DIO5", "DIO6", "DIO7"]
channel_names.extend(["CORE_TIMER", "STREAM_DATA_CAPTURE_16"])

numAddresses = len(channel_names)
aScanList = ljm.namesToAddresses(numAddresses, channel_names)[0]
scanRate = 1000
scansPerRead = int(scanRate / 2)


try:
    # stream resolutio{{n index is 0 (default).
    aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
    aValues = [0, 0]
    numFrames = len(aNames)
    ljm.eWriteNames(t4.handle, numFrames, aNames, aValues)
    # Start streaming
    ljm.eStreamStart(
        handle=t4.handle,
        scansPerRead=scansPerRead,
        scanRate=scanRate,
        aScanList=aScanList,
        numAddresses=len(aScanList),
    )
    print("\nStream started with a scan rate of %0.0f Hz." % scanRate)
    MAX_REQUESTS = 10
    print("\nPerforming %i stream reads." % MAX_REQUESTS)
    start = datetime.now()
    totScans = 0
    totSkip = 0  # Total skipped samples
    i = 1
    data = np.array([])
    last_row = np.array([0] * len(aScanList))
    # transitionTimestamps = {}
    while i <= MAX_REQUESTS:
        aData, deviceScanBacklog, ljmScanBacklog = ljm.eStreamRead(t4.handle)

        core_timer = int(aData[4]) + int(aData[5]) << 16
        data = np.array(aData, dtype=np.int32).reshape((-1, len(aScanList)))

        # combine last to columns into core_time values
        data[:, -2] += data[:, -1] << 16

        # drop last column
        data = data[:, :-1]

        # keep last row of data for transitions of each colum
        last_row = data[-1, :]

        # tansisitions
        transitions = np.diff(data, axis=0)

        # TODO: finish this here

        # core_timer = int(aData[4]) + int(aData[5]) << 16
        # scans = len(aData) / numAddresses
        # totScans += scans

        # Count the skipped samples which are indicated by -9999 values. Missed
        # samples occur after a device's stream buffer overflows and are
        # reported after auto-recover mode ends.
        curSkip = aData.count(-9999.0)
        totSkip += curSkip

        print("\neStreamRead %i" % i)
        ainStr = ""
        for j in range(0, numAddresses):
            ainStr += "%s = %0.5f, " % (channel_names[j], aData[j])
        print("  1st scan out of %i: %s" % (scans, ainStr))
        print(
            f"  Scans Skipped = {curSkip / numAddresses}, Scan Backlogs: Device = {deviceScanBacklog}, LJM = {ljmScanBacklog}"
        )
        i += 1

    end = datetime.now()
    plt.figure()
    plt.plot(data[:, 0:2])
    plt.legend(channel_names[0:2])
    plt.show()

    print("\nTotal scans = %i" % (totScans))
    tt = (end - start).seconds + float((end - start).microseconds) / 1000000
    print("Time taken = %f seconds" % (tt))
    print("LJM Scan Rate = %f scans/second" % (scanRate))
    print("Timed Scan Rate = %f scans/second" % (totScans / tt))
    print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
    print("Skipped scans = %0.0f" % (totSkip / numAddresses))
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

try:
    print("\nStop Stream")
    ljm.eStreamStop(t4.handle)
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)
