# tcpio/server.py

import socket
import threading
from tcpio.protocol import TCPProtocol
from serialio.serial_manager import SerialManager

class TCPServer:
    def __init__(self, host="0.0.0.0", port=8000, port_map=None):
        self.host = host
        self.port = port
        self.clients = {}
        self.running = False
        self.serial_manager = SerialManager(port_map or {
            "GATE_A": "/dev/ttyUSB0"
        })
        self.command_handlers = {
            "GATE_OPEN": self.handle_gate_open,
            "GATE_CLOSED": self.handle_gate_close,
        }

    def start(self):
        self.running = True
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((self.host, self.port))
        server_sock.listen()
        print(f"[TCP 서버 시작] {self.host}:{self.port}")

        try:
            while self.running:
                client_sock, addr = server_sock.accept()
                self.clients[addr] = client_sock
                print(f"[클라이언트 연결] {addr}")
                threading.Thread(
                    target=self.handle_client, 
                    args=(client_sock, addr), 
                    daemon=True
                ).start()
        except KeyboardInterrupt:
            print("[서버 중단됨]")
        finally:
            server_sock.close()
            self.serial_manager.close_all()

    def handle_client(self, client_sock, addr):
        with client_sock:
            while True:
                try:
                    data = client_sock.recv(4096).decode().strip()
                    if not data:
                        print(f"[연결 종료] {addr}")
                        break
                    message = TCPProtocol.parse_message(data)
                    print(f"[수신 from {addr}] {message}")
                    cmd = message.get("cmd", "").strip().upper()
                    print(f"[수신 CMD] {cmd}")

                    handler = self.command_handlers.get(cmd)
                    if handler:
                        handler(client_sock, addr, message)
                    else:
                        print(f"[알림] 알 수 없는 명령: {cmd}")
                                        
                except Exception as e:
                    print(f"[오류] {addr} → {e}")
                    break



    # ---------------- 명령별 핸들러 -----------------------------

    def handle_gate_open(self, client_sock, addr, message):
        gate = message['payload']['gate']
        truck = message['sender']

        self.serial_manager.send_command(gate, "OPEN")
        ack = self.serial_manager.read_response(gate)

        if ack and ack['type'] == "ACK" and ack['result'] == "OK":
            response = TCPProtocol.build_message(
                sender="SERVER",
                receiver=truck,
                cmd="GATE_PASS",
                payload={
                    'gate': gate,
                    "result": "OK"
                }
            )
            client_sock.sendall(response.encode())
            print(f"[응답 to {addr}] {response.strip()}")
        else:
            print(f"[GATE 응답 오류] {ack}")

    def handle_gate_close(self, client_sock, addr, message):
        gate = message['payload']['gate']
        truck = message['sender']

        self.serial_manager.send_command(gate, "CLOSE")
        ack = self.serial_manager.read_response(gate)

        if ack and ack['type'] == "ACK" and ack['result'] == "OK":
            response = TCPProtocol.build_message(
                sender="SERVER",
                receiver=truck,
                cmd="GATE_CLOSED",  # 트럭에게 알릴 응답 명령어
                payload={
                    'gate': gate,
                    "result": "OK"
                }
            )
            client_sock.sendall(response.encode())
        else:
            print(f"[GATE 응답 오류] {ack}")

    # ---------------------------------------------------------

    def stop(self):
        self.running = False
        for sock in self.clients.values():
            sock.close()
        self.serial_manager.close_all()
        print("[TCP 서버 종료됨]")