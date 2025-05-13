from .protocol import TCPProtocol

class TruckCommandSender:
    def __init__(self, truck_sockets: dict):
        self.truck_sockets = truck_sockets
    
    def send(self, truck_id: str, cmd: str, payload: dict = None) -> bool:
        if not self.is_registered(truck_id):
            return False
        
        if payload is None:
            payload = {}
            
        try:
            # RUN 명령 단순화 - target 파라미터 제거
            if cmd == "RUN":
                # 목표 위치가 있더라도 무시하고 단순 RUN 명령만 전송
                payload = {}
            
            # 바이너리 메시지 생성
            message = TCPProtocol.build_message("SERVER", truck_id, cmd, payload)
            
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