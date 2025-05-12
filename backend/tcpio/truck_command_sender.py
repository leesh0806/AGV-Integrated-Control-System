from .protocol import TCPProtocol
import json

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
            
            message = {
                "sender": "SERVER",
                "receiver": truck_id,
                "cmd": cmd,
                "payload": payload
            }
            
            # JSON 직렬화 후 종료 문자 추가
            json_message = json.dumps(message) + "\n"
            
            print(f"[📤 송신 원문] {json.dumps(message)}")
            self.truck_sockets[truck_id].sendall(json_message.encode())
            print(f"[🚚 명령 전송] {truck_id} ← {cmd} | payload={payload}")
            
            # MISSION_ASSIGNED 명령 바로 전송
            if cmd == "RUN" and "mission_id" in (payload or {}) and payload["mission_id"] is not None:
                # 미션 정보 전송 (별도 명령으로)
                mission_payload = {
                    "mission_id": payload["mission_id"],
                    "source": payload.get("source", "LOAD_A")
                }
                
                try:
                    mission_message = {
                        "sender": "SERVER",
                        "receiver": truck_id,
                        "cmd": "MISSION_ASSIGNED",
                        "payload": mission_payload
                    }
                    
                    print(f"[📤 송신 원문] {json.dumps(mission_message)}")
                    if truck_id in self.truck_sockets:
                        self.truck_sockets[truck_id].sendall((json.dumps(mission_message) + "\n").encode())
                        print(f"[🚚 미션 할당 전송] {truck_id} ← MISSION_ASSIGNED | payload={mission_payload}")
                except Exception as e:
                    print(f"[❌ MISSION_ASSIGNED 전송 실패] {truck_id}: {e}")
                
            return True
        except Exception as e:
            print(f"[❌ 전송 실패] {truck_id}: {e}")
            return False

    def is_registered(self, truck_id: str) -> bool:
        return truck_id in self.truck_sockets 