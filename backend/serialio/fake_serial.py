# backend/serialio/fake_serial.py

import queue
import time

class FakeSerial:
    def __init__(self, name="FAKE"):
        self.name = name
        self._queue = queue.Queue()
        self.in_waiting = 0

    def write(self, data: bytes):
        cmd = data.decode().strip()
        print(f"[FakeSerial:{self.name}] 받은 명령: {cmd}")
        time.sleep(0.05)

        if cmd.startswith("GATE") and ("OPEN" in cmd or "CLOSE" in cmd):
            ack = f"ACK:{cmd}:OK\n"
            self._queue.put(ack.encode())
            self.in_waiting += 1

    def readline(self):
        if not self._queue.empty():
            self.in_waiting -= 1
            return self._queue.get()
        return b""

    def close(self):
        print(f"[FakeSerial:{self.name}] 종료")
