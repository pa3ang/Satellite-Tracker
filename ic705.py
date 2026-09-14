import serial
import threading


class IC705:

    MODE = {
        "LSB": 0x00,
        "USB": 0x01,
        "AM":  0x02,
        "CW":  0x03,
        "RTTY":0x04,
        "FM":  0x05,
        "WFM": 0x06,
        "CW-R":0x07,
        "RTTY-R":0x08,
        "DV":  0x17
    }

    def __init__(self, port, baudrate=19200):

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.2,
            rtscts=False,
            dsrdtr=False
        )

        self.ser.setRTS(False)
        self.ser.setDTR(False)

        self.lock = threading.Lock()

    def send(self, data):
        frame = bytearray([0xFE, 0xFE, 0xA4, 0xE0])
        frame.extend(data)
        frame.append(0xFD)

        with self.lock:
            self.ser.write(frame)

    def set_freq(self, freq):
        s = f"{int(freq):010d}"

        data = bytearray([0x05])

        for i in range(8, -1, -2):
            data.append((int(s[i]) << 4) | int(s[i + 1]))

        self.send(data)

    def set_mode(self, mode):

        if isinstance(mode, str):
            mode = self.MODE[mode.upper()]

        self.send(bytearray([0x06, mode]))

    def close(self):
        self.ser.close()