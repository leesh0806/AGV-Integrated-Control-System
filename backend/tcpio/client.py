# backend/tcpio/clinet.py

import socket
from .protocol import TCPProtocol

class TCPClient:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.connected = False

    def connect(self):
        if self.connected:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print(f"[TCP 연결] {self.host}:{self.port}")
            return True
        except Exception as e:
            self.connected = False
            print(f"[TCP 오류] 연결 실패: {e}")
            return False

    def send_command(self, sender: str, receiver: str, cmd: str, payload: dict):
        if not self.connected and not self.connect():
            print("[TCP 오류] 연결되지 않아 메시지를 전송할 수 없습니다")
            return
            
        message = TCPProtocol.build_message(sender, receiver, cmd, payload)
        try:
            self.sock.sendall(message)
            print(f"[TCP Send] 명령: {cmd}, 페이로드: {payload}")
        except Exception as e:
            self.connected = False
            print(f"[TCP 오류] 전송 실패: {e}")

    def read_response(self):
        if not self.connected and not self.connect():
            print("[TCP 오류] 연결되지 않아 응답을 읽을 수 없습니다")
            return None
            
        try:
            # 헤더(4바이트) 먼저 읽기
            header_data = self.sock.recv(4)
            if not header_data or len(header_data) < 4:
                print("[TCP 오류] 헤더 수신 실패")
                self.connected = False
                return None
                
            # 헤더에서 페이로드 길이 추출
            _, _, _, payload_len = header_data[0], header_data[1], header_data[2], header_data[3]
            
            # 페이로드 읽기
            payload_data = b''
            if payload_len > 0:
                payload_data = self.sock.recv(payload_len)
                if len(payload_data) < payload_len:
                    print("[TCP 오류] 페이로드 수신 실패")
                    self.connected = False
                    return None
            
            # 전체 메시지 파싱
            raw_data = header_data + payload_data
            parsed = TCPProtocol.parse_message(raw_data)
            print(f"[TCP Read] {parsed}")
            return parsed
        except Exception as e:
            self.connected = False
            print(f"[TCP 오류] 수신 실패: {e}")
            return None
        
    def close(self):
        self.sock.close()
        self.connected = False
        print(f"[TCP] 연결 종료")