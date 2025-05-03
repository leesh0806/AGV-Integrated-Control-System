# backend/tcpio/server.py

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
            #"GATE_A": "/dev/ttyUSB0"
        })
        self.command_handlers = {
            # 게이트
            "GATE_OPEN": self.handle_gate_open,
            "GATE_CLOSED": self.handle_gate_close,
            # 트럭
            "OBSTACLE": self.handle_obstacle
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
            client_sock.sendall(b"RUN\n")
            print(f"[자동 명령] RUN 전송 → {addr}")
            
            buffer = ""

            while True:
                try:
                    data = client_sock.recv(4096).decode()
                    if not data:
                        print(f"[연결 종료] {addr}")
                        break

                    buffer += data

                    # 줄바꿈 기준으로 JSON 메시지 분리
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        message = TCPProtocol.parse_message(line)
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
        pass

    def handle_gate_close(self, client_sock, addr, message):
        pass

    # ---------------------------------------------------------

    def handle_obstacle(self, client_sock, addr, message):
        truck = message.get("sender", "UNKNOWN_TRUCK")
        payload = message.get("payload", {})

        position = payload.get("position", "UNKNOWN")
        distance = payload.get("distance_cm", -1)
        timestamp = payload.get("timestamp", "")
        detected = payload.get("detected", "UNKNOWN")

        if (detected == "DETECTED"):
            print(f"[장애물 감지] 트럭={truck}, 위치={position}, 거리={distance}cm, 시간={timestamp}")
        elif (detected == "CLEARED"):
            print(f"[장애물 해제] 트럭={truck}, 위치={position}, 시간={timestamp}")
        else:
            print(f"[경고] 감지 여부 파악 불가: detected={detected}")

        # # 응답 메시지 생성 및 전송
        # response = TCPProtocol.build_message(
        #     sender="SERVER",
        #     receiver=truck,
        #     cmd="ACK",
        #     payload={
        #         "ref_cmd": "OBSTACLE",
        #         "detected": detected,
        #         "received_at": timestamp
        #     }
        # )

        # client_sock.sendall(response.encode())
        # print(f"[응답 전송 완료] {response.strip()}")

    # ---------------------------------------------------------

    def stop(self):
        self.running = False
        for sock in self.clients.values():
            sock.close()
        self.serial_manager.close_all()
        print("[TCP 서버 종료됨]")