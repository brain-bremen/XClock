import nidaqmx
from nidaqmx.constants import LineGrouping
import time
import numpy as np
import csv
import matplotlib.pyplot as plt
import os


# Function to write data to CSV
def write_data_to_csv(filename, data, timestamps):
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["Timestamp (s)", "Camera 1 Frame Clock", "Camera 2 Frame Clock"]
        )
        for i in range(len(data)):
            writer.writerow([timestamps[i], data[i][0], data[i][1]])


# Function to plot the first 3 seconds of the data
def plot_frame_clocks(timestamps, data):
    # Convert lists to numpy arrays for easier handling
    timestamps = np.array(timestamps)
    data = np.array(data)

    # Only plot the first 3 seconds
    max_time = 3
    mask = timestamps <= max_time

    # Plot Camera 1 and Camera 2 frame clocks
    plt.figure(figsize=(10, 6))
    plt.plot(
        # timestamps[mask],
        timestamps,
        data[:, 0],
        label="Imaging Source (Cam 1)",
        color="blue",
        linewidth=1,
    )
    plt.plot(
        # timestamps[mask],
        timestamps,
        data[:, 1],
        label="Inscopix (Cam 2)",
        color="red",
        linewidth=1,
    )

    # Adding titles and labels
    plt.title("Camera Frame Clock Signals (First 3 Seconds)")
    plt.xlabel("Time (s)")
    plt.ylabel("Frame Clock TTL Signal")
    plt.legend()
    plt.grid(True)

    # Show the plot
    plt.show()


# Main function
def main():
    # User input for acquisition time (seconds)
    animal_id = int(input("Enter the animal ID: "))
    session_id = int(input("Enter the session ID: "))
    acquisition_time = float(input("Enter the total acquisition time (in seconds): "))

    # DAQ device names (adjust based on your setup)
    trigger_port = "Dev1/port0/line0"  # Digital Output for Trigger
    cam1_frame_clock_port = (
        "Dev1/port0/line2"  # Digital Input for Camera 1 Frame Clock, Imaging Source
    )
    cam2_frame_clock_port = (
        "Dev1/port0/line4"  # Digital Input for Camera 2 Frame Clock, Inscopix
    )

    # Initialize data storage
    cam_data = []
    timestamps = []

    # Create tasks for both Camera 1 and Camera 2 frame clocks
    with nidaqmx.Task() as cam1_task, nidaqmx.Task() as cam2_task:
        # Configure digital input channels for the frame clocks
        cam1_task.di_channels.add_di_chan(
            cam1_frame_clock_port, line_grouping=LineGrouping.CHAN_PER_LINE
        )
        cam2_task.di_channels.add_di_chan(
            cam2_frame_clock_port, line_grouping=LineGrouping.CHAN_PER_LINE
        )

        # Start the tasks for frame clock acquisition
        cam1_task.start()
        cam2_task.start()

        # Record the start time
        start_time = time.time()
        current_time = start_time

        # Start acquiring frame clock signals before triggering the cameras
        print("Starting frame clock acquisition...")

        # Data acquisition loop for the 500ms before the trigger
        while (current_time - start_time) < 0.5:
            # Read the state of the frame clock signals (TTL)
            cam1_signal = cam1_task.read()
            cam2_signal = cam2_task.read()

            # Get the timestamp
            timestamp = current_time - start_time

            # Store the data
            cam_data.append([cam1_signal, cam2_signal])
            timestamps.append(timestamp)

            # Sleep for a short period to simulate sampling rate (e.g., 1 ms)
            time.sleep(0.001)

            # Update current time
            current_time = time.time()

        print("500 ms delay completed. Triggering cameras...")

        # Create a task to trigger the cameras
        with nidaqmx.Task() as trigger_task:
            # Configure digital output channel
            trigger_task.do_channels.add_do_chan(
                trigger_port, line_grouping=LineGrouping.CHAN_PER_LINE
            )

            # Set the trigger to HIGH and keep it HIGH throughout the acquisition
            trigger_task.write(True)  # Set the trigger to HIGH

            # Continue data acquisition for the remaining time after the trigger
            remaining_time = acquisition_time - 0.5
            current_time = time.time()

            while (current_time - start_time) < acquisition_time:
                # Read the state of the frame clock signals (TTL)
                cam1_signal = cam1_task.read()
                cam2_signal = cam2_task.read()

                # Get the timestamp
                timestamp = current_time - start_time

                # Store the data
                cam_data.append([cam1_signal, cam2_signal])
                timestamps.append(timestamp)

                # Sleep for a short period to simulate sampling rate (e.g., 1 ms)
                time.sleep(0.001)

                # Update current time
                current_time = time.time()

            # Set the trigger to LOW after the entire acquisition time is completed
            trigger_task.write(False)  # Set the trigger to LOW

    # Save the collected data for post-hoc analysis
    save_directory = r"C:\Users\Admin\arne"
    os.makedirs(save_directory, exist_ok=True)
    file_name = os.path.join(
        save_directory,
        f"sert_{animal_id}_session_{session_id}_camera_frame_clock_data.csv",
    )
    write_data_to_csv(file_name, cam_data, timestamps)
    print(f"Data acquisition complete. Data saved to '{file_name}'.")

    # Plot the first 3 seconds of the frame clock data
    plot_frame_clocks(timestamps, cam_data)


if __name__ == "__main__":
    main()
