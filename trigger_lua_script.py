from labjack import ljm
import time


def upload_lua_script():
    # Open LabJack device
    handle = ljm.openS("T4", "USB", "ANY")

    # Your Lua script as a string
    lua_script = """
    MB.W(2000, 0, 0)         -- Disable EF on DIO0
    MB.W(2001, 0, 0)         -- Set EF index to 0 (PWM)
    MB.W(2002, 3, 40000)     -- Duty cycle
    MB.W(2003, 3, 80000)     -- Roll value for 1 kHz
    MB.W(2000, 0, 1)         -- Enable EF on DIO0

    local pulseCount = 0
    local maxPulses = 100
    local interval = 1000

    LJ.IntervalConfig(0, interval)

    while true do
    if LJ.CheckInterval(0) then
        pulseCount = pulseCount + 1
        if pulseCount >= maxPulses then
        MB.W(2000, 0, 0)
        break
        end
    end
    end
    """

    # Stop any running script
    ljm.eWriteName(handle, "LUA_RUN", 0)
    time.sleep(0.5)

    # Upload and run the script
    script_bytes = bytearray(lua_script, "utf-8")
    ljm.eWriteName(handle, "LUA_SOURCE_SIZE", len(script_bytes))
    ljm.eWriteNameByteArray(handle, "LUA_SOURCE_WRITE", len(script_bytes), script_bytes)
    ljm.eWriteName(handle, "LUA_RUN", 1)

    print("Lua script uploaded and running.")
    ljm.close(handle)


def send_trigger():
    handle = ljm.openS("T4", "USB", "ANY")

    # Write trigger value to USER_RAM0_U16
    ljm.eWriteName(handle, "USER_RAM0_U16", 12345)

    print("Trigger sent to Lua script.")
    ljm.close(handle)


def main():
    upload_lua_script()
    send_trigger()


if __name__ == "__main__":
    main()
