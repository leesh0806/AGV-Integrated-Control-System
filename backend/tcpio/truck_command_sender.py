from .protocol import TCPProtocol

class TruckCommandSender:
    def __init__(self, truck_sockets: dict):
        self.truck_sockets = truck_sockets
        self.truck_status_manager = None  # 트럭 상태 관리자 참조 추가
    
    # 트럭 상태 관리자 설정 메소드 추가
    def set_truck_status_manager(self, truck_status_manager):
        # 이미 동일한 객체가 설정되어 있으면 중복 메시지 출력 안 함
        if self.truck_status_manager is not truck_status_manager:
            self.truck_status_manager = truck_status_manager
            print(f"[✅ 트럭 상태 관리자 설정] truck_status_manager가 command_sender에 설정되었습니다.")
    
    def send(self, truck_id: str, cmd: str, payload: dict = None) -> bool:
        if not self.is_registered(truck_id):
            return False
        
        if payload is None:
            payload = {}
            
        try:
            # FINISH_LOADING 명령어 특수 처리
            if cmd == "FINISH_LOADING":
                # position 값이 없거나 유효하지 않은 경우 확인
                if "position" not in payload or not payload["position"] or payload["position"] == "UNKNOWN":
                    # 트럭 상태 관리자를 통해 현재 위치 확인
                    if self.truck_status_manager:
                        try:
                            context = self.truck_status_manager.get_truck_context(truck_id)
                            if context and hasattr(context, 'position') and context.position:
                                current_position = context.position
                                if current_position in ["LOAD_A", "LOAD_B"]:
                                    print(f"[⚠️ position 보정] FINISH_LOADING의 position이 유효하지 않아 컨텍스트 위치({current_position})로 대체")
                                    payload["position"] = current_position
                                else:
                                    print(f"[⚠️ position 보정] 컨텍스트 위치({current_position})가 적재 위치가 아니므로 기본값 LOAD_A로 설정")
                                    payload["position"] = "LOAD_A"
                            else:
                                print(f"[⚠️ position 보정] 트럭 컨텍스트를 찾을 수 없어 기본값 LOAD_A로 설정")
                                payload["position"] = "LOAD_A"
                        except Exception as e:
                            print(f"[⚠️ position 보정 오류] {e} - 기본값 LOAD_A 사용")
                            payload["position"] = "LOAD_A"
                    else:
                        # 기본값으로 LOAD_A 설정
                        print(f"[⚠️ position 보정] FINISH_LOADING의 position이 없거나 유효하지 않아 기본값 LOAD_A로 설정")
                        payload["position"] = "LOAD_A"
                
                # position 값 유효성 다시 검증
                if payload["position"] not in ["LOAD_A", "LOAD_B"]:
                    print(f"[⚠️ position 재보정] 유효하지 않은 position 값({payload['position']})을 LOAD_A로 강제 변경")
                    payload["position"] = "LOAD_A"
            
            # RUN 명령 단순화 - target 파라미터 제거
            elif cmd == "RUN":
                # target만 유지하고 나머지 파라미터는 제거
                if "target" in payload:
                    target = payload["target"]
                    payload = {"target": target}
                else:
                    # 목표 위치가 없으면 빈 페이로드 사용
                    payload = {}
            
            # 바이너리 메시지 생성
            message = TCPProtocol.build_message("SERVER", truck_id, cmd, payload)
            
            # 메시지 전송 및 로깅
            print(f"[📤 송신] {truck_id} ← {cmd} | payload={payload}")
            self.truck_sockets[truck_id].sendall(message)
            
            # MISSION_ASSIGNED 명령 바로 전송 - mission_id가 있을 경우
            if cmd == "RUN" and "mission_id" in (payload or {}) and payload["mission_id"] is not None:
                # 미션 정보 전송 (별도 명령으로)
                # 단순화된 형식 - source만 포함
                mission_payload = {
                    "source": payload.get("source", "LOAD_A")
                }
                
                try:
                    # 바이너리 메시지 생성
                    mission_message = TCPProtocol.build_message("SERVER", truck_id, "MISSION_ASSIGNED", mission_payload)
                    
                    if truck_id in self.truck_sockets:
                        self.truck_sockets[truck_id].sendall(mission_message)
                        print(f"[🚚 미션 할당 전송] {truck_id} ← MISSION_ASSIGNED | payload={mission_payload}")
                except Exception as e:
                    print(f"[❌ MISSION_ASSIGNED 전송 실패] {truck_id}: {e}")
                
            return True
        except Exception as e:
            print(f"[❌ 전송 실패] {truck_id}: {e}")
            return False

    def is_registered(self, truck_id: str) -> bool:
        return truck_id in self.truck_sockets

    def _handle_command(self, truck_id, cmd, payload=None):
        """명령 처리 및 전송"""
        if payload is None:
            payload = {}
            
        # 명령별 특수 처리
        if cmd == "FINISH_LOADING":
            # position 값이 없거나 유효하지 않은 경우 확인
            if "position" not in payload or not payload["position"] or payload["position"] == "UNKNOWN":
                # 트럭 ID로 현재 위치 파악 시도
                truck_context = self.truck_status_manager.get_truck_context(truck_id) if self.truck_status_manager else None
                if truck_context and hasattr(truck_context, 'position') and truck_context.position:
                    position = truck_context.position
                    # 적재 위치인 경우만 설정
                    if position in ["LOAD_A", "LOAD_B"]:
                        print(f"[⚠️ position 보정] FINISH_LOADING의 position이 없거나 유효하지 않아 트럭의 현재 위치({position})로 대체")
                        payload["position"] = position
                    else:
                        # 적재 위치가 아닌 경우 기본값으로 LOAD_A 설정
                        print(f"[⚠️ position 보정] 적재 위치가 아닌 {position}에서 기본값 LOAD_A로 대체")
                        payload["position"] = "LOAD_A"
                else:
                    # 컨텍스트를 찾을 수 없는 경우 기본값으로 LOAD_A 설정
                    print(f"[⚠️ position 보정] 트럭 컨텍스트를 찾을 수 없어 기본값 LOAD_A로 설정")
                    payload["position"] = "LOAD_A"
                
        # 명령 전송
        message = self.protocol.build_message(
            sender=self.sender_id,
            receiver=truck_id,
            cmd=cmd,
            payload=payload
        )
        
        # 실제 전송 수행
        try:
            self.tcp_server.send_packet(truck_id, message)
            print(f"[📤 송신] {truck_id} ← {cmd} | payload={payload}")
            return True
        except Exception as e:
            print(f"[❌ 송신 오류] {truck_id} ← {cmd}: {e}")
            return False 