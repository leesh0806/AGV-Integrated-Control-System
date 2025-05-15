from typing import Dict, Optional, List
from datetime import datetime
from .facility_status_db import FacilityStatusDB

class FacilityStatusManager:
    def __init__(self, db: FacilityStatusDB):
        self.facility_status_db = db
        self.gate_status = {}
        self.belt_status = {}
        self.dispenser_status = {}  # 디스펜서 상태 추가
        self.command_sender = None  # 트럭 명령 전송자
    
    # -------------------------------- 트럭 명령 전송자 설정 --------------------------------
    
    def set_command_sender(self, command_sender):
        """트럭 명령 전송자 설정"""
        self.command_sender = command_sender
        print("[✅ 명령 전송자 설정 완료] facility_status_manager.command_sender 설정됨")
        
        # 명령 전송자가 실제로 존재하는지 검증
        if self.command_sender:
            try:
                # 간단한 테스트 로깅
                print(f"[✅ 명령 전송자 검증] 명령 전송자 설정 성공: {type(self.command_sender).__name__}")
            except Exception as e:
                print(f"[⚠️ 명령 전송자 오류] 명령 전송자 검증 중 오류: {e}")
        else:
            print("[❌ 명령 전송자 누락] command_sender가 None으로 설정되었습니다.")
    
    # -------------------------------- 시설 상태 초기화 --------------------------------
    
    def reset_all_facilities(self):
        """모든 시설 상태를 초기화"""
        self.gate_status = {}  # 메모리 상의 게이트 상태 초기화
        self.belt_status = {}  # 메모리 상의 벨트 상태 초기화
        self.dispenser_status = {}  # 메모리 상의 디스펜서 상태 초기화
        
        # DB 상태도 초기화
        self.facility_status_db.reset_all_statuses()
        print("[✅ 메모리 상태 초기화 완료] 모든 시설 상태가 초기화되었습니다")
        
        # 기본 상태 추가
        self.update_gate_status("GATE_A", "CLOSED", "IDLE")
        self.update_gate_status("GATE_B", "CLOSED", "IDLE")
        self.update_belt_status("BELT", "STOPPED", "IDLE", "EMPTY")
        self.update_dispenser_status("DISPENSER", "CLOSED", "ROUTE_A", "IDLE")
    
    # -------------------------------- 게이트 상태 관리 --------------------------------
    
    def update_gate_status(self, gate_id: str, state: str, operation: str):
        """게이트 상태 업데이트"""
        # DB에 로깅
        self.facility_status_db.log_gate_status(
            gate_id=gate_id,
            state=state,
            operation=operation
        )
        
        # 메모리 상태 업데이트
        self.gate_status[gate_id] = {
            "state": state,
            "operation": operation,
            "timestamp": datetime.now()
        }
        
        # 상태 변화 로깅
        print(f"[🚪 게이트 상태] {gate_id}: {state} (동작: {operation})")
    
    def get_gate_status(self, gate_id: str) -> dict:
        """게이트 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        # DB에서 최신 상태 조회
        gate_data = self.facility_status_db.get_latest_gate_status(gate_id)
        
        # 초기 상태
        gate_status = {
            "state": "CLOSED",
            "operation": "IDLE",
            "timestamp": datetime.now()
        }
        
        if gate_data:
            gate_status = {
                "state": gate_data["state"],
                "operation": gate_data["operation"],
                "timestamp": gate_data["timestamp"]
            }
        
        # 메모리 상태 업데이트
        self.gate_status[gate_id] = gate_status
        
        return gate_status
    
    # -------------------------------- 벨트 상태 관리 --------------------------------
    
    def update_belt_status(self, belt_id: str, state: str, operation: str, container_state: str):
        """벨트 상태 업데이트"""
        # DB에 로깅
        self.facility_status_db.log_belt_status(
            belt_id=belt_id,
            state=state,
            operation=operation,
            container_state=container_state
        )
        
        # 메모리 상태 업데이트
        self.belt_status[belt_id] = {
            "state": state,
            "operation": operation,
            "container_state": container_state,
            "timestamp": datetime.now()
        }
        
        # 상태 변화 로깅
        print(f"[🧭 벨트 상태] {belt_id}: {state} (동작: {operation}, 컨테이너: {container_state})")
    
    def get_belt_status(self, belt_id: str) -> dict:
        """벨트 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        # DB에서 최신 상태 조회
        belt_data = self.facility_status_db.get_latest_belt_status(belt_id)
        
        # 초기 상태
        belt_status = {
            "state": "STOPPED",
            "operation": "IDLE",
            "container_state": "EMPTY",
            "timestamp": datetime.now()
        }
        
        if belt_data:
            belt_status = {
                "state": belt_data["state"],
                "operation": belt_data["operation"],
                "container_state": belt_data["container_state"],
                "timestamp": belt_data["timestamp"]
            }
        
        # 메모리 상태 업데이트
        self.belt_status[belt_id] = belt_status
        
        return belt_status
    
    # -------------------------------- 디스펜서 상태 관리 --------------------------------
    
    def update_dispenser_status(self, dispenser_id: str, state: str, position: str, operation: str):
        """디스펜서 상태 업데이트"""
        # DB에 로깅
        self.facility_status_db.log_dispenser_status(
            dispenser_id=dispenser_id,
            state=state,
            position=position,
            operation=operation
        )
        
        # 메모리 상태 업데이트
        self.dispenser_status[dispenser_id] = {
            "state": state,
            "position": position,
            "operation": operation,
            "timestamp": datetime.now()
        }
        
        # 상태 변화 로깅
        print(f"[🔄 디스펜서 상태] {dispenser_id}: {state} (위치: {position}, 동작: {operation})")
        
        # LOADED 상태일 때 truck_fsm_manager에 알림
        if state == "LOADED" and operation == "LOADED":
            print(f"[🌟 디스펜서 적재 완료 감지] {dispenser_id}가 적재 완료 상태로 업데이트됨")
            
            # 명령 전송자가 있는 경우 트럭에게 알림
            if self.command_sender:
                try:
                    # 디스펜서 컨트롤러에서 현재 트럭 ID 가져오기 시도
                    # 먼저 현재 모듈에서 Main Controller 접근 시도
                    truck_id = "TRUCK_01"  # 기본값
                    
                    # 직접 FSM 매니저 접근 시도
                    try:
                        import sys
                        from backend.main_controller.main_controller import MainController
                        
                        # MainController 인스턴스 찾기
                        main_controller = None
                        for module in sys.modules.values():
                            if hasattr(module, 'main_controller') and isinstance(module.main_controller, MainController):
                                main_controller = module.main_controller
                                break
                        
                        if main_controller:
                            truck_fsm_manager = getattr(main_controller, 'truck_fsm_manager', None)
                            if truck_fsm_manager and truck_fsm_manager.dispenser_controller:
                                # 디스펜서 컨트롤러에서 트럭 ID 가져오기
                                if hasattr(truck_fsm_manager.dispenser_controller, 'current_truck_id'):
                                    truck_id = truck_fsm_manager.dispenser_controller.current_truck_id
                                    print(f"[✅ 트럭 ID 찾음] 디스펜서 컨트롤러에서 트럭 ID '{truck_id}' 찾음")
                    except Exception as e:
                        print(f"[⚠️ 트럭 ID 찾기 오류] {e}")
                    
                    print(f"[📤 DISPENSER_LOADED 명령 전송] 트럭 {truck_id}에게 적재 완료 알림")
                    success = self.command_sender.send(truck_id, "DISPENSER_LOADED", {
                        "dispenser_id": dispenser_id,
                        "position": position
                    })
                    print(f"[적재 완료 알림 결과] {'성공' if success else '실패'}")
                    
                    # 직접 FSM 매니저 통지 시도 (백업)
                    if not success:
                        print(f"[🔄 백업 시도] 명령 전송 실패, FSM 매니저 직접 호출 시도")
                        try:
                            if main_controller and truck_fsm_manager:
                                print(f"[🔄 FSM 직접 호출] truck_fsm_manager.handle_trigger 시도")
                                truck_fsm_manager.handle_trigger(truck_id, "DISPENSER_LOADED", {
                                    "dispenser_id": dispenser_id,
                                    "position": position
                                })
                        except Exception as e:
                            print(f"[⚠️ FSM 직접 호출 오류] {e}")
                    
                except Exception as e:
                    print(f"[⚠️ 적재 완료 알림 오류] {e}")
            else:
                print(f"[❌ 명령 전송자 없음] command_sender가 설정되지 않아 트럭에게 적재 완료를 알릴 수 없습니다.")
    
    def get_dispenser_status(self, dispenser_id: str) -> dict:
        """디스펜서 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        # DB에서 최신 상태 조회
        dispenser_data = self.facility_status_db.get_latest_dispenser_status(dispenser_id)
        
        # 초기 상태
        dispenser_status = {
            "state": "CLOSED",
            "position": "ROUTE_A",
            "operation": "IDLE",
            "timestamp": datetime.now()
        }
        
        if dispenser_data:
            dispenser_status = {
                "state": dispenser_data["state"],
                "position": dispenser_data["position"],
                "operation": dispenser_data["operation"],
                "timestamp": dispenser_data["timestamp"]
            }
        
        # 메모리 상태 업데이트
        self.dispenser_status[dispenser_id] = dispenser_status
        
        return dispenser_status
    
    # -------------------------------- 모든 시설 상태 조회 --------------------------------
    
    def get_all_facilities(self) -> Dict[str, dict]:
        """모든 시설의 상태 조회"""
        result = {}
        
        # 게이트 상태 조회
        gate_ids = ["GATE_A", "GATE_B"]
        for gate_id in gate_ids:
            result[gate_id] = self.get_gate_status(gate_id)
        
        # 벨트 상태 조회
        belt_ids = ["BELT"]
        for belt_id in belt_ids:
            result[belt_id] = self.get_belt_status(belt_id)
            
        # 디스펜서 상태 조회
        dispenser_ids = ["DISPENSER"]
        for dispenser_id in dispenser_ids:
            result[dispenser_id] = self.get_dispenser_status(dispenser_id)
        
        return result
    
    # -------------------------------- 히스토리 조회 --------------------------------
    
    def get_gate_history(self, gate_id: str, limit: int = 100) -> List[Dict]:
        """게이트 히스토리 조회"""
        return self.facility_status_db.get_gate_history(gate_id, limit)
    
    def get_belt_history(self, belt_id: str, limit: int = 100) -> List[Dict]:
        """벨트 히스토리 조회"""
        return self.facility_status_db.get_belt_history(belt_id, limit)
        
    def get_dispenser_history(self, dispenser_id: str, limit: int = 100) -> List[Dict]:
        """디스펜서 히스토리 조회"""
        return self.facility_status_db.get_dispenser_history(dispenser_id, limit)
    
    def close(self):
        """리소스 정리"""
        self.facility_status_db.close()
        print("[DEBUG] FacilityStatusManager 리소스 정리 완료")
