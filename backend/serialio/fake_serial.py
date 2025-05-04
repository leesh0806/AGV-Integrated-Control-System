# backend/serialio/fake_serial.py

import threading

class FakeSerial:
    def __init__(self, name="TRUCK_01"):
        self.name = name
        self.buffer = []
        self.in_waiting = 0
        self.lock = threading.Lock()

    def write(self, data: bytes):
        msg = data.decode().strip()
        print(f"[FakeSerial:{self.name}] 받은 명령: {msg}")

        response = self._simulate_response(msg)
        if response:
            with self.lock:
                self.buffer.append((response + "\n").encode())
                self.in_waiting = len(self.buffer)

    def readline(self):
        with self.lock:
            if self.buffer:
                return self.buffer.pop(0)
            return b""

    def _simulate_response(self, msg: str):
        # ✅ 게이트 명령 시뮬레이션
        if msg.startswith("GATE_"):
            parts = msg.split("_")
            if len(parts) == 3:
                gate_id = f"{parts[0]}_{parts[1]}"
                action = parts[2]
                if action == "OPEN":
                    return f"ACK:{gate_id}_OPENED"
                elif action == "CLOSE":
                    return f"ACK:{gate_id}_CLOSED"

        # ✅ 벨트 명령 시뮬레이션
        elif msg == "BELTACT":
            threading.Timer(0.5, self._enqueue_response, args=["STATUS:BELT:RUNNING"]).start()
            threading.Timer(20, self._enqueue_response, args=["STATUS:BELT:STOPPED"]).start()
            return "ACK:BELT:STARTED"
        elif msg == "BELTOFF":
            return "ACK:BELT:STOPPED"
        elif msg == "EMRSTOP":
            return "ACK:BELT:EMERGENCY_STOP"

        return None

    def _enqueue_response(self, response):
        with self.lock:
            self.buffer.append((response + "\n").encode())
            self.in_waiting = len(self.buffer)

    def close(self):
        pass
