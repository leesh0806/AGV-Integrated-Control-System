from backend.controller.app_controller import AppController
from backend.tcpio.server import TCPServer
from backend.mission.mission import Mission
import signal
import sys

# ✅ 가짜 DB 클래스
class FakeMissionDB:
    def save_mission(self, mission):
        print(f"[FAKE_DB] 미션 저장됨 → {mission.mission_id}")

    def update_mission_completion(self, mission_id, status_code, status_label, timestamp_completed):
        print(f"[FAKE_DB] 미션 완료 기록됨 → {mission_id} ({status_label})")

    def load_all_active_and_waiting_missions(self):
        return []

# 설정
HOST = '0.0.0.0'
PORT = 8001  # 포트 번호 변경

# 포트 맵: 시리얼 장치 연결에 사용됨
port_map = {
    "GATE_A": "VIRTUAL_GATE_A",
    "GATE_B": "VIRTUAL_GATE_B",
    "BELT": "VIRTUAL_BELT"
}

# ✅ AppController 인스턴스 생성 및 미션 불러오기
app = AppController(port_map=port_map, use_fake=True)
app.mission_manager.db = FakeMissionDB()  # 가짜 DB 설정

# ✅ 테스트용 미션 추가
print("[🔧 테스트용 미션 추가 중...]")
test_mission = Mission(
    mission_id="TEST_001",
    cargo_type="MINERAL",
    cargo_amount=100,
    source="LOAD_A",
    destination="BELT"
)
app.mission_manager.add_mission(test_mission)
print(f"[✅ 미션 추가됨] {test_mission.mission_id}")

# ✅ TCP 서버 실행
server = TCPServer(HOST, PORT, app)

# 종료 신호 핸들링
def signal_handler(sig, frame):
    print("[🛑 서버 종료 요청됨]")
    server.stop()  # 올바른 종료 메서드 호출
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print(f"[✅ 서버 시작됨] {HOST}:{PORT}")
server.start()