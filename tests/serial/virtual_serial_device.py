import threading
import time
import queue

class VirtualSerialDevice:
    def __init__(self):
        self.in_buffer = queue.Queue()
        self.out_buffer = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._device_loop)
        self.thread.daemon = True
        self.thread.start()

    def _device_loop(self):
        while self.running:
            if not self.in_buffer.empty():
                command = self.in_buffer.get()
                print(f"[가상장치] 수신: {command.strip()}")
                time.sleep(0.5)
                if command.startswith("GATE_A_OPEN"):
                    self.out_buffer.put("ACK:GATE_A_OPEN:OK\n")
                elif command.startswith("GATE_A_CLOSE"):
                    self.out_buffer.put("ACK:GATE_A_CLOSE:OK\n")
                else:
                    self.out_buffer.put("ACK:UNKNOWN:FAIL\n")
            time.sleep(0.1)

    def write(self, data: bytes):
        self.in_buffer.put(data.decode())

    def readline(self) -> bytes:
        try:
            return self.out_buffer.get(timeout=1).encode()
        except queue.Empty:
            return b''
        
    def in_waiting(self):
        return not self.out_buffer.empty()
    
    def close(self):
        self.running = False
        self.thread.join()