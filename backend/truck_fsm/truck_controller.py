from typing import TYPE_CHECKING
import time
import traceback
from .truck_state import TruckState

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
            
            # ✅ 트럭 소켓 등록 상태 확인 및 업데이트
            try:
                if hasattr(self.truck_fsm_manager, 'command_sender') and self.truck_fsm_manager.command_sender:
                    command_sender = self.truck_fsm_manager.command_sender
                    # STATUS_UPDATE를 수신했으나 트럭이 등록되어 있지 않은 경우 등록 시도
                    if not command_sender.is_registered(truck_id):
                        # tcp_server 인스턴스를 가져와 소켓 등록 시도
                        if hasattr(self.truck_fsm_manager, 'app') and hasattr(self.truck_fsm_manager.app, 'tcp_server'):
                            tcp_server = self.truck_fsm_manager.app.tcp_server
                            # 현재 연결된 모든 소켓을 확인하여 해당 트럭 ID의 소켓을 찾아 등록
                            for client_addr, client_sock in tcp_server.clients.items():
                                # 트럭 ID와 소켓을 연결하여 등록
                                tcp_server.truck_sockets[truck_id] = client_sock
                                # command_sender에 업데이트된 truck_sockets 설정
                                tcp_server.app.set_truck_commander(tcp_server.truck_sockets)
                                print(f"[🔄 트럭 소켓 자동 등록] STATUS_UPDATE 수신 시 {truck_id} 소켓이 자동으로 등록되었습니다.")
                                break
            except Exception as e:
                print(f"[⚠️ 트럭 소켓 등록 시도 실패] {e}")
                
            # 타임스탬프는 이제 서버에서 생성
            timestamp = time.time()
            
            # 배터리 상태 업데이트
            battery_level = payload.get("battery_level", 0)
            
            # FSM 상태 확인
            is_charging = False  # 기본 값
            if hasattr(self.truck_fsm_manager, 'fsm'):
                context = self.truck_fsm_manager.fsm._get_or_create_context(truck_id)
                current_state = context.state
                if current_state == TruckState.CHARGING:
                    is_charging = True
                    print(f"[상태 확인] {truck_id}는 현재 충전 상태입니다. FSM 상태: {current_state.name}")
            
            if isinstance(battery_level, (int, float)):
                # 배터리 상태 업데이트 전 이전 상태 확인
                prev_battery_level = 100.0  # 기본값
                if hasattr(self.truck_fsm_manager, 'fsm'):
                    context = self.truck_fsm_manager.fsm._get_or_create_context(truck_id)
                    prev_battery_level = context.battery_level
                
                # 배터리 상태 업데이트
                self.truck_status_manager.update_battery(truck_id, battery_level, is_charging)
                
                # FSM 매니저의 컨텍스트에도 배터리 정보 업데이트
                if hasattr(self.truck_fsm_manager, 'fsm'):
                    context = self.truck_fsm_manager.fsm._get_or_create_context(truck_id)
                    context.battery_level = battery_level
                    context.is_charging = is_charging
                
                # 배터리가 95% 이상이고 충전 중이면 자동으로 충전 완료 처리
                if battery_level >= 95 and is_charging:
                    print(f"[🔋 자동 충전 완료] {truck_id}의 배터리가 95% 이상에 도달했습니다. 충전 상태를 해제합니다.")
                    self.truck_status_manager.update_battery(truck_id, battery_level, False)
                    if hasattr(self.truck_fsm_manager, 'fsm'):
                        context.is_charging = False
                        context.state = TruckState.IDLE  # 명시적으로 IDLE 상태로 전환
                    
                    # 충전 완료 이벤트 전송
                    self.truck_fsm_manager.handle_trigger(truck_id, "FINISH_CHARGING", {})
            
            # 위치 정보 업데이트
            position = payload.get("position", "UNKNOWN")
            
            # position이 문자열인 경우 (바이너리 프로토콜)
            if isinstance(position, str):
                location = position
                run_state = "IDLE"  # 기본 값
                
                # 위치가 UNKNOWN이면 이전 위치 유지 또는 STANDBY로 설정
                if location == "UNKNOWN" and hasattr(self.truck_fsm_manager, 'fsm'):
                    context = self.truck_fsm_manager.fsm._get_or_create_context(truck_id)
                    if context.position and context.position != "UNKNOWN":
                        location = context.position
                        print(f"[위치 유지] {truck_id}: 위치=UNKNOWN 수신됨, 이전 위치({location}) 유지")
                    else:
                        # 완전히 초기 상태인 경우 STANDBY로 가정
                        location = "STANDBY"
                        print(f"[위치 초기화] {truck_id}: 위치=UNKNOWN 수신됨, 기본 위치(STANDBY)로 설정")
                
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
            # 기존 딕셔너리 형태의 position 처리 (기존 JSON 프로토콜 호환성 유지)
            elif isinstance(position, dict):
                # current 또는 location 키로 위치 데이터 가져오기
                location = position.get("current", position.get("location", "UNKNOWN"))
                # run_state 또는 status 키로 상태 데이터 가져오기
                run_state = position.get("run_state", position.get("status", "IDLE"))
                
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
            
            # ✅ 다시 한번 소켓 등록 상태 확인
            if hasattr(self.truck_fsm_manager, 'command_sender') and self.truck_fsm_manager.command_sender:
                command_sender = self.truck_fsm_manager.command_sender
                if command_sender.is_registered(truck_id):
                    print(f"[✅ 트럭 소켓 확인] {truck_id} 소켓이 정상적으로 등록되어 있습니다.")
                else:
                    print(f"[⚠️ 트럭 소켓 미등록] {truck_id} 소켓이 아직 등록되지 않았습니다.")
                    
            print(f"[✅ 상태 업데이트 완료] {truck_id}")
            
        except Exception as e:
            print(f"[❌ 상태 업데이트 오류] {e}")
            traceback.print_exc() 