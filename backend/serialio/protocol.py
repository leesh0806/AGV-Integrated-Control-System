# backend/serialio/protocol.py

class SerialProtocol:
    # 예: "GATE_A", "OPEN" -> "GATE_A_OPEN\n"
    @staticmethod
    def build_command(target: str, action: str) -> str:
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