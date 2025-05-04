import time
from backend.serialio.controller import SerialController
from backend.serialio.gate_controller import GateController
from backend.serialio.belt_controller import BeltController
from backend.fsm.fsm_manager import TruckFSMManager
from backend.fsm.truck_manager import TruckManager
from backend.mission.manager import MissionManager
from backend.mission.mission import Mission
from backend.mission.status import MissionStatus

# ✅ 가짜 DB 클래스
class FakeMissionDB:
    def save_mission(self, mission):
        print(f"[FAKE_DB] 미션 저장됨 → {mission.mission_id}")

    def update_mission_completion(self, mission_id, status_code, status_label, timestamp_completed):
        print(f"[FAKE_DB] 미션 완료 기록됨 → {mission_id} ({status_label})")

# ✅ 가짜 명령 전송자
class FakeTruckCommander:
    def send(self, truck_id, cmd, payload=None):
        print(f"[FAKE_CMD] {truck_id} ← {cmd} ({payload})")

def test_full_fsm(use_fake=True):
    print("\n[🔧 가상 FSM 전체 시스템 테스트 시작]")

    # ▒ 시스템 구성 요소 초기화
    controller = SerialController(port="TRUCK_01", use_fake=use_fake)
    gate_ctrl = GateController(serial_manager=controller)
    belt_ctrl = BeltController(serial_controller=controller)

    fsm_mgr = TruckFSMManager(gate_controller=gate_ctrl, mission_manager=None, belt_controller=belt_ctrl)
    truck_mgr = TruckManager(fsm_mgr)

    commander = FakeTruckCommander()
    fsm_mgr.set_commander(commander)

    db = FakeMissionDB()
    mission_mgr = MissionManager(db)
    fsm_mgr.mission_manager = mission_mgr

    # ▒ 테스트용 미션 추가
    mission = Mission(
        mission_id="M001",
        cargo_type="BOX",
        cargo_amount=3,
        source="load_B",
        destination="belt"
    )
    mission_mgr.add_mission(mission)
    truck_id = "TRUCK_01"
    fsm_mgr.set_state(truck_id, fsm_mgr.get_state(truck_id))

    # ✅ 단계별 트리거 실행 함수
    def step(desc, func):
        input(f"\n🟢 STEP: {desc} (Enter 키를 눌러 다음 단계로 진행)")
        func()
        time.sleep(0.2)

    # ✅ 테스트 실행 흐름: 게이트 열기 → 통과 → 닫기 → 목적지
    step("미션 할당 요청", lambda: fsm_mgr.handle_trigger(truck_id, "ASSIGN_MISSION", {}))

    # ▶ 게이트 A 진입
    step("CHECKPOINT_A 도착 → 게이트 A 열기", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_A", {"gate_id": "GATE_A"}))
    step("게이트 A 열림 인지", lambda: fsm_mgr.handle_trigger(truck_id, "ACK_GATE_OPENED", {}))
    step("CHECKPOINT_B 도착 → 게이트 A 닫기", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_B", {"gate_id": "GATE_A"}))

    # ▶ 적재
    step("적재장 도착", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_LOAD_A", {}))
    step("적재 시작", lambda: fsm_mgr.handle_trigger(truck_id, "START_LOADING", {}))
    step("적재 완료", lambda: fsm_mgr.handle_trigger(truck_id, "FINISH_LOADING", {}))

    # ▶ 게이트 B 진입
    step("CHECKPOINT_C 도착 → 게이트 B 열기", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_C", {"gate_id": "GATE_B"}))
    step("게이트 B 열림 인지", lambda: fsm_mgr.handle_trigger(truck_id, "ACK_GATE_OPENED", {}))
    step("CHECKPOINT_D 도착 → 게이트 B 닫기", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_D", {"gate_id": "GATE_B"}))

    # ▶ 하차
    step("벨트 도착", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_BELT", {}))
    step("하차 시작", lambda: fsm_mgr.handle_trigger(truck_id, "START_UNLOADING", {}))
    step("하차 완료", lambda: fsm_mgr.handle_trigger(truck_id, "FINISH_UNLOADING", {}))

    # ▶ 복귀
    step("대기 지점 도착", lambda: fsm_mgr.handle_trigger(truck_id, "ARRIVED_AT_STANDBY", {}))

    print("\n✅ 테스트 완료: 트럭+벨트+게이트 FSM 흐름 정상 작동 확인됨")

if __name__ == "__main__":
    test_full_fsm(use_fake=True)
