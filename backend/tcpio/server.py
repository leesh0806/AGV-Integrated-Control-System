# backend/tcpio/server.py

import socket
import threading
from tcpio.protocol import TCPProtocol
from controller.app_controller import AppController


class TCPServer:
    def __init__(self, host="0.0.0.0", port=8000, app=None):
        self.host = host
        self.port = port
        self.clients = {}         # addr → socket
        self.truck_sockets = {}   # truck_id → socket
        self.running = False
        self.app = app if app else AppController(port_map={})
        self.app.set_truck_commander(self.truck_sockets)

    def start(self):
        self.running = True
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((self.host, self.port))
        server_sock.listen()
        print(f"[🚀 TCP 서버 시작] {self.host}:{self.port}")

        try:
            while self.running:
                client_sock, addr = server_sock.accept()
                self.clients[addr] = client_sock
                print(f"[✅ 클라이언트 연결됨] {addr}")
                threading.Thread(
                    target=self.handle_client,
                    args=(client_sock, addr),
                    daemon=True
                ).start()
        except KeyboardInterrupt:
            print("[🛑 서버 종료 요청됨]")
        finally:
            self.stop()
            server_sock.close()

    def handle_client(self, client_sock, addr):
        with client_sock:
            client_sock.sendall(b"RUN\n")  # 자동 시작 명령
            print(f"[📤 RUN 전송] {addr}")

            buffer = ""
            while True:
                try:
                    data = client_sock.recv(4096).decode()
                    if not data:
                        print(f"[❌ 연결 종료] {addr}")
                        break

                    buffer += data

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        message = TCPProtocol.parse_message(line)
                        print(f"[📥 수신] {addr} → {message}")

                        if message:
                            # sender 기반 socket 등록
                            truck_id = message.get("sender")
                            if truck_id:
                                self.truck_sockets[truck_id] = client_sock
                                
                            self.app.handle_message(message)

                except Exception as e:
                    print(f"[⚠️ 에러] {addr} → {e}")
                    break

    def stop(self):
        self.running = False
        for sock in self.clients.values():
            try:
                sock.close()
            except:
                pass
        print("[🔌 TCP 서버 종료됨]")
