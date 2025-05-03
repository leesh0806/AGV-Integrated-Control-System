# backend/run_tcp_server.py

from tcpio.server import TCPServer
from controller.app_controller import AppController

if __name__ == "__main__":
    # 포트 매핑 (하드웨어 환경에 맞게 수정)
    port_map = {}

    # AppController 초기화
    app = AppController(port_map)

    # TCP 서버 실행
    server = TCPServer(port=8000, app=app)
    try:
        server.start()
    except KeyboardInterrupt:
        print("[서버 종료 요청]")
        server.stop()