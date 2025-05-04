from backend.controller.app_controller import AppController
from backend.tcpio.server import TCPServer
from backend.mission.mission import Mission
from backend.mission.db import MissionDB
import signal
import sys, os
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.truck_status_api import app as flask_app

# 설정
HOST = '0.0.0.0'
PORT = 8001

# 포트 맵: 시리얼 장치 연결에 사용됨
port_map = {
    "GATE_A": "VIRTUAL_GATE_A",
    "GATE_B": "VIRTUAL_GATE_B",
    "BELT": "VIRTUAL_BELT"
}

# ✅ DB 연결 설정
db = MissionDB(
    host="localhost",
    user="root",
    password="jinhyuk2dacibul",
    database="dust"
)

# ✅ AppController 인스턴스 생성
app = AppController(port_map=port_map, use_fake=True)
app.mission_manager.db = db  # 실제 DB 설정

# ✅ DB에서 미션 로드
app.mission_manager.load_from_db()

# ✅ 기존 미션 확인
print("[🔍 기존 미션 확인 중...]")
existing_missions = db.load_all_active_and_waiting_missions()
if not existing_missions:
    print("[🔧 새로운 테스트 미션 추가 중...]")
    test_mission = Mission(
        mission_id="TEST_001",
        cargo_type="MINERAL",
        cargo_amount=100,
        source="LOAD_A",
        destination="BELT"
    )
    app.mission_manager.add_mission(test_mission)
    print(f"[✅ 미션 추가됨] {test_mission.mission_id}")
else:
    print(f"[ℹ️ 기존 미션 발견] 총 {len(existing_missions)}개의 미션이 있습니다.")

# ✅ TCP 서버 실행
server = TCPServer(HOST, PORT, app)

def run_flask():
    flask_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

# 종료 신호 핸들링
def signal_handler(sig, frame):
    print("[🛑 서버 종료 요청됨]")
    server.stop()
    db.close()  # DB 연결 종료
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print(f"[✅ 서버 시작됨] {HOST}:{PORT}")
print(f"[🚀 TCP 서버 시작] {HOST}:{PORT}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    server.start()