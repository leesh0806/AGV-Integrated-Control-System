# tcpio/server.py

import socket
import threading
from tcpio.protocol import TCPProtocol

class TCPServer:
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.clients = {}
        self.running = False

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
                threading.Thread(target=self.handle_client, args=(client_sock, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("[서버 중단됨]")
        finally:
            server_sock.close()

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

                    print(f"[수신 CMD] {message.get('cmd')}")

                    # 여기에서 로직 구현: 미션 전송, 응답 전송 등 ---------

                    # 예시

                    if message.get("cmd") == "OPEN_GATE":
                        response = TCPProtocol.build_message(
                            sender="SERVER",
                            receiver=message["sender"],
                            cmd="ACK_GATE",
                            payload={"result": "OK"}
                        )
                        client_sock.sendall(response.encode())
                        print(f"[응답 to {addr}] {response.strip()}")
                                        
                    # ----------------------------------------------
                except Exception as e:
                    print(f"[오류] {addr} → {e}")
                    break

    def stop(self):
        self.running = False
        for sock in self.clients.values():
            sock.close()
        print("[TCP 서버 종료됨]")