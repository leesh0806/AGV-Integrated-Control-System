# backend/serialio/protocol.py
# 시리얼 명령 포맷 정의

class SerialProtocol:
    @staticmethod
    def build_command(target: str, action: str) -> str:
        # 예: "GATE_A", "OPEN" -> "GATE_A_OPEN\n"
        return f"{target.upper()}_{action.upper()}\n"
    
    @staticmethod
    def parse_response(response: str) -> dict:
        parts = response.strip().split(":")
        if parts[0] == "ACK" and len(parts) == 3:
            return {
                "type": "ACK",
                "command": parts[1],
                "result":parts[2]
            }
        elif parts[0] == "STATUS" and len(parts) == 3:
            return {
                "type": "STATUS",
                "target": parts[1],
                "state": parts[2]
            }
        return {
            "type": "UNKNOWN", 
            "raw": response.strip()
        }