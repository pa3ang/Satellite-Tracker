# Satellite Tracker

**Satellite Tracker** is a Python application for making QSOs using amateur-radio satellites and controlling an Icom IC-705. Reception is provided by the Maasbree WebSDR on port 8909, while the uplink transmission is made from the home station. The program combines the satellite downlink frequency with the calculated Doppler shift and calculates the corresponding uplink frequency for the radio.

The project is developed for use on Linux and is primarily intended for amateur-radio operators.

## Features

* Satellite tracking
* Graphical user interface
* Icom IC-705 CAT control
* Automatic calculation of satellite Doppler shift
* Automatic setting of the IC-705 frequency
* Setting of the IC-705 operating mode
* TX frequency offset support for satellite transponder frequency correction
* WebSDR frequency monitoring
* External WebSDR support, including automatic Audio Start
* Satellite settings through an INI file
* Automatic download of current TLE data
* Suitable for satellite operation and monitoring
* Designed to run on multiple platforms
* Note: designed and tested with the Maasbree WebSDR on port 8909

## Project files

| File | Description |
|---|---|
| `main.py` | Main application and graphical user interface |
| `ic705.py` | Communication and CAT control for the Icom IC-705 |
| `websdr.py` | Opens the WebSDR and reads the receiver frequency |
| `sattracker.ini` | Application, radio, WebSDR and satellite settings |
| `icon.png` | Application icon |

## Requirements

The program requires:

- Python 3
- Tkinter
- Skyfield
- Playwright
- An Icom IC-705
- USB connection between the computer and the IC-705
- Internet connection for TLE data and WebSDR functionality

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

The application reads its configuration from `sattracker.ini`.

## Configuration

The main settings are stored in `sattracker.ini`. This keeps the program configuration separate from the Python source code.

The INI file contains settings for the tracker, IC-705, WebSDR and individual satellites.

### Tracker settings

The `[tracker]` section contains the general tracker settings.

Typical settings include:

| Setting | Description |
|---|---|
| `default_satellite` | Satellite selected when the program starts |
| `update_ms` | Tracking update interval in milliseconds |
| `pass_search_days` | Number of days used when searching for satellite passes |
| `tx_offset_step` | Step size used for changing the TX offset |

### IC-705 settings

The `[ic705]` section contains the IC-705 connection settings.

| Setting | Description |
|---|---|
| `port` | Serial/CAT port used by the IC-705 |
| `baudrate` | CAT communication speed |

The IC-705 port can be specified using a stable Linux device path such as:

```text
/dev/serial/by-id/...
```

This is preferable to a changing device name such as `/dev/ttyACM0`.

### Location and calculation settings

The INI file also contains the station location and calculation parameters.

| Setting | Description |
|---|---|
| `locator` | Maidenhead locator of the station |
| `height` | Station height above sea level in metres |
| `speed_of_light` | Speed of light used for Doppler calculations |
| `local_tz` | Local timezone |

For the current station configuration the locator is `JO32AM`, the height is 8 metres and the timezone is `Europe/Amsterdam`.

### WebSDR settings

The `[websdr]` section contains the WebSDR URL.

The current WebSDR is:

```text
http://sdr.websdrmaasbree.nl:8909/
```

The WebSDR is operated manually by the user through its normal web interface.

SatTracker **only reads the current receiver frequency** from the WebSDR.

It does **not**:

- change the WebSDR frequency;
- change the WebSDR mode;
- change the WebSDR band;
- control the WebSDR.

The received WebSDR frequency is used to keep the IC-705 frequency synchronized.

## Satellite settings

Each satellite has its own section in the INI file.

The current configuration contains:

- RS-44
- FO-29
- ISS

The sections are:

```text
[satellite_RS-44]
[satellite_FO-29]
[satellite_ISS]
```

Satellite-specific settings can include the satellite name, NORAD identifier, frequencies and TX offset.

This makes it possible to change satellite parameters without modifying `main.py`.

## TLE data

SatTracker downloads current TLE data when the program starts.

The configured source is:

```text
https://www.amsat.org/tle/current/dailytle.txt
```

The TLE data is used by Skyfield to calculate the satellite position and Doppler shift.

## Doppler calculation

SatTracker continuously calculates the Doppler shift for the selected satellite.

Separate Doppler values are calculated for:

- RX frequency
- TX frequency

The calculated TX Doppler shown in the GUI is the **actual calculated Doppler shift**, without the configured TX offset.

The TX offset is nevertheless included when calculating the frequency that is sent to the IC-705.

For example:

```text
Calculated TX Doppler:  +1250 Hz
TX offset:               +600 Hz
IC-705 correction:      +1850 Hz
```

This allows the displayed Doppler value and the additional station-specific TX correction to remain clearly separated.

Additionally, this makes it possible to fine-tune the uplink frequency based on what is heard on the downlink.

## Icom IC-705

The Satellite Tracker communicates with the IC-705 through its CAT interface.

The radio must be connected to the computer using USB and the configured serial/CAT interface must be available to the program.

The IC-705 is used to set:

- operating frequency
- operating mode

For reliable operation, make sure that:

- the IC-705 is switched on;
- the USB connection is active;
- the configured CAT interface is available;
- no other program is exclusively using the same serial interface.

## WebSDR

The WebSDR functionality uses the Maasbree WebSDR as an external receiver.

The WebSDR is opened by SatTracker using Playwright. The user operates the WebSDR through its normal web interface.

SatTracker only reads the current receiver frequency.

The communication is therefore one-way:

```text
WebSDR
   |
   | receiver frequency
   v
SatTracker
   |
   | CAT frequency/mode
   v
IC-705
```

No frequency, mode or band information is sent back to the WebSDR by SatTracker.

## IC-705 operating mode

When using the WebSDR synchronization function, the IC-705 should be operated in **VFO mode**.

Do not use:

- Split mode
- Duplex mode

The synchronization controls the normal VFO frequency of the IC-705.

The operating mode of the IC-705 is controlled separately by SatTracker according to the selected satellite configuration and tracking requirements.

## Operating principle

The basic principle is:

```text
                         TLE data
                            |
                            v
                    +---------------+
                    |  Satellite    |
                    |   tracking    |
                    +---------------+
                            |
                            | Doppler calculation
                            v
                    +---------------+
                    |  SatTracker    |
                    |    Python      |
                    +---------------+
                       ^         |
                       |         |
             WebSDR frequency   | CAT
                       |         |
                       |         v
                    WebSDR      IC-705
                                  |
                                  v
                             Antenna system
```

The satellite position is calculated from the current TLE data.

The resulting Doppler correction is used to control the IC-705.

The WebSDR can independently be used as a remote receiver. SatTracker reads its frequency and transfers that frequency to the IC-705.

## Satellite operation

A typical setup can consist of:

```text
                       Internet
                          |
             +------------+------------+
             |                         |
             v                         v
        TLE data                    WebSDR
             |                         |
             +------------+------------+
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

This allows the operator to use the WebSDR for remote signal monitoring while the IC-705 is controlled locally.

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