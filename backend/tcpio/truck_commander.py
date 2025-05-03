# backend/tcpio/truck_commander.py

from tcpio.protocol import TCPProtocol

class TruckCommandSender:
    def __init__(self, truck_sockets: dict):
        self.truck_sockets = truck_sockets
    
    def send(self, truck_id: str, cmd: str, payload: dict = {}):
        sock = self.truck_sockets.get(truck_id)
        if not sock:
            print(f"[❌ TruckCommandSender] 트럭 '{truck_id}'의 소켓을 찾을 수 없습니다.")
            return
        
        msg = TCPProtocol.build_message("SERVER", truck_id, cmd, payload)
        try:
            sock.sendall((msg + "\n").encode())
            print(f"[🚚 명령 전송] {truck_id} ← {cmd} | payload={payload}")
        except Exception as e:
            print(f"[❌ 전송 실패] {truck_id} → {e}")