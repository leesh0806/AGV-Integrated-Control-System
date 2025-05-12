from typing import TYPE_CHECKING
import time
import traceback

if TYPE_CHECKING:
    from .truck_fsm_manager import TruckFSMManager
    from ..truck_status.truck_status_manager import TruckStatusManager


class TruckController:
    def __init__(self, truck_fsm_manager: 'TruckFSMManager'):
        self.truck_fsm_manager = truck_fsm_manager
        self.truck_status_manager = None
        print("[✅ 트럭 컨트롤러 초기화 완료]")

    def set_status_manager(self, truck_status_manager: 'TruckStatusManager'):
        self.truck_status_manager = truck_status_manager
        print(f"[✅ 트럭 컨트롤러에 상태 관리자 설정됨]")

    def handle_message(self, msg: dict):
        try:
            sender = msg.get("sender")
            cmd = msg.get("cmd", "").strip().upper()
            payload = msg.get("payload", {})

            print(f"[📨 TruckController] sender={sender}, cmd={cmd}")

            if not sender:
                print("[TruckController] sender가 없음")
                return

            # 상태 업데이트 메시지 처리
            if cmd == "STATUS_UPDATE":
                self._handle_status_update(sender, payload)
                return
            
            # HELLO 명령은 트럭 등록을 위한 초기 명령이므로 무시
            if cmd == "HELLO":
                print(f"[TruckController] 트럭 등록 확인: {sender}")
                return
                
            # 기본 명령 처리 - FSM 매니저의 handle_trigger를 통해 이벤트 전달
            self.truck_fsm_manager.handle_trigger(sender, cmd, payload)
                
        except Exception as e:
            print(f"[❌ 메시지 처리 오류] {e}")
            traceback.print_exc()
            
    def _handle_status_update(self, truck_id: str, payload: dict):
        try:
            # 트럭 상태 매니저 없으면 무시
            if not self.truck_status_manager:
                print("[TruckController] 트럭 상태 매니저가 설정되지 않음")
                return
                
            # 타임스탬프 확인
            timestamp = payload.get("timestamp", time.time())
            
            # 배터리 상태 업데이트
            battery_data = payload.get("battery", {})
            if battery_data:
                level = battery_data.get("level", 0)
                is_charging = battery_data.get("is_charging", False)
                self.truck_status_manager.update_battery(truck_id, level, is_charging)
                
                # FSM 매니저의 컨텍스트에도 배터리 정보 업데이트
                if hasattr(self.truck_fsm_manager, 'fsm'):
                    context = self.truck_fsm_manager.fsm._get_or_create_context(truck_id)
                    context.battery_level = level
                    context.is_charging = is_charging
                
                # 배터리가 100%이고 충전 중이면 자동으로 충전 완료 처리
                if level >= 100 and is_charging:
                    print(f"[🔋 자동 충전 완료] {truck_id}의 배터리가 100%에 도달했습니다. 충전 상태를 해제합니다.")
                    self.truck_status_manager.update_battery(truck_id, level, False)
                    if hasattr(self.truck_fsm_manager, 'fsm'):
                        context.is_charging = False
                    
                    # 현재 FSM 상태가 CHARGING이면 FINISH_CHARGING 트리거 발생
                    current_fsm_state = self.truck_fsm_manager.get_state(truck_id)
                    state_name = getattr(current_fsm_state, 'name', str(current_fsm_state))
                    if "CHARGING" in state_name:
                        self.truck_fsm_manager.handle_trigger(truck_id, "FINISH_CHARGING", {})
            
            # 위치 정보 업데이트
            position_data = payload.get("position", {})
            if position_data:
                # current 또는 location 키로 위치 데이터 가져오기
                location = position_data.get("current", position_data.get("location", "UNKNOWN"))
                # run_state 또는 status 키로 상태 데이터 가져오기
                run_state = position_data.get("run_state", position_data.get("status", "IDLE"))
                
                print(f"[위치 업데이트] {truck_id}: 위치={location}, 상태={run_state}")
                
                # 위치와 상태 모두 업데이트 (FSM 상태는 건드리지 않음)
                self.truck_status_manager.update_position(truck_id, location, run_state)
                
                # FSM 매니저의 컨텍스트에도 위치 정보 업데이트
                if hasattr(self.truck_fsm_manager, 'fsm') and location != "UNKNOWN":
                    context = self.truck_fsm_manager.fsm._get_or_create_context(truck_id)
                    old_position = context.position
                    if old_position != location:
                        context.position = location
                        print(f"[위치 변경 감지] {truck_id}: {old_position} → {location}")
                        
                        # 위치 변경에 따른 이벤트 발생
                        self.truck_fsm_manager.fsm.handle_position_update(
                            truck_id, location, {"run_state": run_state}
                        )
                
                # run_state에 따른 추가 트리거 처리
                if run_state in ["LOADING", "UNLOADING"]:
                    print(f"[작업 상태 감지] {truck_id}: {run_state}")
                    
                    if run_state == "LOADING":
                        self.truck_fsm_manager.handle_trigger(truck_id, "START_LOADING", {})
                    elif run_state == "UNLOADING":
                        self.truck_fsm_manager.handle_trigger(truck_id, "START_UNLOADING", {})
            
            print(f"[✅ 상태 업데이트 완료] {truck_id}")
            
        except Exception as e:
            print(f"[❌ 상태 업데이트 오류] {e}")
            traceback.print_exc() 