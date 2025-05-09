import signal
import sys, os

# 현재 스크립트 경로를 기준으로 프로젝트 루트 경로를 추가합니다
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.main_controller.main_controller import MainController
from backend.tcpio.server import TCPServer
from backend.mission.mission import Mission
from backend.mission.mission_db import MissionDB
from backend.mission.mission_status import MissionStatus
import threading
from backend.api.api import app as flask_app

# 설정
HOST = '0.0.0.0'
PORT = 8001

# 포트 맵: 시리얼 장치 연결에 사용됨
port_map = {
    "GATE_A": "GATE_A",  # 가상 장치는 이름을 그대로 사용
    "GATE_B": "GATE_B",  # 가상 장치는 이름을 그대로 사용
    "BELT": "BELT"
}

print("[초기화] 포트 맵:", port_map)

# DB 연결 설정
mission_db = MissionDB(
    host="localhost",
    user="root",
    password="jinhyuk2dacibul",
    database="dust"
)

# MainController 인스턴스 생성
app = MainController(port_map=port_map, use_fake=True)

# 기존 미션 확인
print("[🔍 기존 미션 확인 중...]")
waiting_missions = mission_db.get_waiting_missions()
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
    waiting_missions = mission_db.get_waiting_missions()
    for mission_data in waiting_missions:
        mission = Mission.from_row(mission_data)
        app.mission_manager.cancel_mission(mission.mission_id)
    print(f"[✅ {len(waiting_missions)}개의 미션이 취소되었습니다.]")
    
    server.stop()
    mission_db.close()  # DB 연결 종료
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