# tcpio/clinet.py

import socket
from tcpio.protocol import TCPProtocol

class TCPClient:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)

    def connect(self):
        try:
            self.sock.connect((self.host, self.port))
            print(f"[TCP 연결] {self.host}:{self.port}")
        except Exception as e:
            print(f"[TCP 오류] 전송 실패: {e}")

    def send_command(self, sender: str, receiver: str, cmd: str, payload: dict):
        message = TCPProtocol.build_message(sender, receiver, cmd, payload)
        try:
            self.sock.sendall(message.encode())
            print(f"[TCP Send] {message.strip()}")
        except Exception as e:
            print(f"[TCP 오류] 전송 실패: {e}")

    def read_response(self):
        try:
            data = self.sock.recv(4096).decode().strip()
            parsed = TCPProtocol.parse_message(data)
            print(f"[TCP Read] {parsed}")
            return parsed
        except Exception as e:
            print(f"[TCP 오류] 수신 실패: {e}")
            return None
        
    def close(self):
        self.sock.close()
        print(f"[TCP] 연결 종료")