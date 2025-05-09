from backend.controller.app_controller import AppController
from backend.tcpio.server import TCPServer
from backend.mission.mission import Mission
from backend.mission.db import MissionDB
from backend.mission.status import MissionStatus
import signal
import sys, os
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api.truck_monitoring_api import app as flask_app

# 설정
HOST = '0.0.0.0'
PORT = 8001

# 포트 맵: 시리얼 장치 연결에 사용됨
port_map = {
    "GATE_A": "GATE_A",  # 가상 장치는 이름을 그대로 사용
    "GATE_B": "GATE_B",  # 가상 장치는 이름을 그대로 사용
    "BELT": "BELT"
}

print("[✅ 초기화] 포트 맵:", port_map)

# DB 연결 설정
db = MissionDB(
    host="localhost",
    user="root",
    password="jinhyuk2dacibul",
    database="dust"
)

# AppController 인스턴스 생성
app = AppController(port_map=port_map, use_fake=True)
app.mission_manager.db = db  # 실제 DB 설정

# 기존 미션 확인
print("[🔍 기존 미션 확인 중...]")
waiting_missions = db.get_waiting_missions()
print(f"[ℹ️ 기존 미션 발견] 총 {len(waiting_missions)}개의 대기 중인 미션이 있습니다.")

# TCP 서버 실행
server = TCPServer(HOST, PORT, app)

# Flask 서버 실행 함수
def run_flask():
    flask_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

# 종료 신호 핸들링
def signal_handler(sig, frame):
    print("[🛑 서버 종료 요청됨]")
    
    # 실행 중인 모든 미션을 취소 상태로 변경
    print("[⚠️ 실행 중인 미션 취소 중...]")
    assigned_missions = db.get_assigned_missions()
    for mission in assigned_missions:
        app.mission_manager.cancel_mission(mission.mission_id)
    print(f"[✅ {len(assigned_missions)}개의 미션이 취소되었습니다.]")
    
    server.stop()
    db.close()  # DB 연결 종료
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print(f"[메인 서버 시작됨] TCP 서버: {HOST}:{PORT}, Flask 서버: 0.0.0.0:5001")


if __name__ == "__main__":
    # Flask 서버를 별도 데몬 스레드로 시작
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # TCP 서버를 메인 스레드에서 시작
    server.start() 