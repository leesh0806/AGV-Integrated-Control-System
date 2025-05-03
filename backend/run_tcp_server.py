from controller.app_controller import AppController
from tcpio.server import TCPServer
import signal
import sys

# 설정
HOST = '0.0.0.0'
PORT = 8000

# 포트 맵: 시리얼 장치 연결에 사용됨
port_map = {
    # 예: "GATE_A": "/dev/ttyUSB0"
}

# ✅ AppController 인스턴스 생성 및 미션 불러오기
app = AppController(port_map=port_map)
app.mission_manager.load_from_db()

# ✅ TCP 서버 실행
server = TCPServer(HOST, PORT, app)

# 종료 신호 핸들링
def signal_handler(sig, frame):
    print("[🛑 서버 종료 요청됨]")
    server.stop()  # 올바른 종료 메서드 호출
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# 메인 루프
server.start()
