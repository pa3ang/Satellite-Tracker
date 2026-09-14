# Satellite Tracker

**Satellite Tracker** is a Python application for tracking amateur-radio satellites and controlling an Icom IC-705. The program combines satellite tracking information with automatic frequency and mode control of the radio.

The project is developed for use on Linux and is primarily intended for amateur-radio operators.

## Features

- Satellite tracking
- Graphical user interface
- Icom IC-705 control
- Automatic setting of:
  - frequency
  - operating mode
- WebSDR frequency and mode monitoring
- Communication with an external WebSDR
- Suitable for satellite operation and monitoring
- Designed to run on Linux Mint and other Linux distributions

## Project files

| File | Description |
|---|---|
| `main.py` | Main application and graphical user interface |
| `ic705.py` | Communication and CAT control for the Icom IC-705 |
| `websdr.py` | Communication with the WebSDR and reading the receiver frequency |
| `icon.png` | Application icon |

## Requirements

The program requires:

- Python 3
- Tkinter
- An Icom IC-705
- USB connection between the computer and the IC-705
- Internet connection for the WebSDR functionality

The application has been developed and tested on:

- Linux Mint
- Python 3
- Icom IC-705

## Installation

Clone the repository:

```bash
git clone https://github.com/pa3ang/Satellite-Tracker.git
```

Enter the project directory:

```bash
cd Satellite-Tracker
```

Run the application:

```bash
python3 main.py
```

If Python reports a missing module, install the required module with `pip3` or through the Linux package manager as appropriate for your distribution.

## Satellites

Currently, the program supports three satellites:

- RS-44
- FO-29
- ISS

## Settings

The settings need to be adjusted to match your station setup.

| Setting | Description |
|---|---|
| `TLE_URL` | Leave unchanged. This is used to download the latest Kepler TLE data when the program starts. |
| `LOCAL_TZ` | Adjust if needed. Use the same format as shown in the program. |
| `IC705_PORT` | Change according to your system. On Windows, this can be a COM port. |
| `IC705_BAUDRATE` | Change if your system requires a different baud rate. |
| `TX_OFFSET_STEP` | Leave unchanged. |
| `DEFAULT_TX_OFFSET` | Leave unchanged. This value is overridden for individual satellites where required. |
| `SPEED_OF_LIGHT` | Leave unchanged. |
| `LOCATOR` | Change to your Maidenhead locator. |
| `HEIGHT` | Change to the height of your station above sea level, in metres. |
| `WEBSDR_URL` | Leave unchanged unless you want to use another WebSDR. |

## Icom IC-705

The Satellite Tracker communicates with the IC-705 through its CAT interface.

The radio must be connected to the computer using USB and the appropriate serial/CAT interface must be available to the program.

The IC-705 is used to set the operating frequency and mode.

For reliable operation, make sure that:

- the IC-705 is switched on;
- the USB connection is active;
- the correct CAT interface is available;
- no other program is exclusively using the same serial interface.

## WebSDR

The WebSDR functionality allows the application to monitor an external WebSDR.

The WebSDR itself is operated through its normal web interface. The Satellite Tracker does not need to operate the complete WebSDR interface.

Instead, the program reads the relevant receiver information, such as:

- receive frequency
- operating mode

This information can then be transferred to the IC-705.

This makes it possible to use a WebSDR as a remote receiver while keeping the IC-705 synchronized with the received frequency and mode.

## Operating principle

The basic principle is:

```text
             WebSDR
                |
                | frequency / mode
                v
          +-------------+
          |  SatTracker |
          |   Python    |
          +-------------+
                |
                | CAT
                v
             IC-705
```

The WebSDR remains under the control of the operator through its normal web interface.

The Satellite Tracker reads the receiver information and sends the corresponding frequency and mode to the IC-705.

## IC-705 operating mode

When using the WebSDR synchronization function, the IC-705 should be operated in **VFO mode**.

Do not use:

- Split mode
- Duplex mode

The purpose of the synchronization is to control the normal VFO frequency and mode of the IC-705.

## Satellite operation

The application can be used as part of an amateur-radio satellite station.

A typical setup can consist of:

```text
                    Internet
                       |
                       v
                   WebSDR
                       |
                       v
                Satellite Tracker
                       |
                       v
                    IC-705
                       |
                       v
                  Antenna system
```

The WebSDR can be used for monitoring signals while the IC-705 is controlled locally.

## Running the program

From the project directory:

```bash
cd ~/SatTracker
python3 main.py
```

For development or troubleshooting, running the program from a terminal is recommended because error messages are then visible.

## GitHub

The source code is maintained on GitHub:

**PA3ANG Satellite Tracker**

https://github.com/pa3ang/Satellite-Tracker

## Author

**PA3ANG**

Amateur Radio since 1977.

## License

This project is provided as an amateur-radio project for personal and experimental use.

If you want to use, modify, or redistribute the software, please check the repository for the applicable license information.

---

## Notes

This project is under development. Features and implementation details may change as the Satellite Tracker is further developed.

73,

**PA3ANG**