from backend.controller.app_controller import AppController
from backend.tcpio.server import TCPServer
from backend.mission.mission import Mission
from backend.mission.db import MissionDB
from backend.mission.status import MissionStatus
import signal
import sys, os
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api.truck_status_api import app as flask_app

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
waiting_missions = db.load_all_waiting_missions()
print(f"[ℹ️ 기존 미션 발견] 총 {len(waiting_missions)}개의 대기 중인 미션이 있습니다.")

# ✅ TCP 서버 실행
server = TCPServer(HOST, PORT, app)

def run_flask():
    flask_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

# 종료 신호 핸들링
def signal_handler(sig, frame):
    print("[🛑 서버 종료 요청됨]")
    
    # 실행 중인 모든 미션을 취소 상태로 변경
    print("[⚠️ 실행 중인 미션 취소 중...]")
    assigned_missions = db.load_all_assigned_missions()
    for mission_data in assigned_missions:
        mission = Mission(
            mission_id=mission_data[0],
            cargo_type=mission_data[1],
            cargo_amount=mission_data[2],
            source=mission_data[3],
            destination=mission_data[4]
        )
        mission.status = MissionStatus[mission_data[5]]
        mission.cancel()
        db.save_mission(mission)
    print(f"[✅ {len(assigned_missions)}개의 미션이 취소되었습니다.]")
    
    server.stop()
    db.close()  # DB 연결 종료
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print(f"[✅ 서버 시작됨] {HOST}:{PORT}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    server.start()