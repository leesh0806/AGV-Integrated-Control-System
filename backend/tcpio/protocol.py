# tcpio/protocol.py

import json

class TCPProtocol:
    @staticmethod
    def build_message(sender: str, receiver: str, cmd: str, payload: dict) -> str:
        return json.dumps({
            "sender": sender,
            "receiver": receiver,
            "cmd": cmd,
            "payload": payload
        }) + "\n"
    
    @staticmethod
    def parse_message(raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except Exception:
            return {
                "type": "INVALID",
                "raw": raw.strip()
            }
