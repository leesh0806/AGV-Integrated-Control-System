# backend/tcpio/protocol.py

import struct
import datetime

class TCPProtocol:
    # 코드 정의
    # 트럭 → PC 명령어
    CMD_ARRIVED = 0x01
    CMD_OBSTACLE = 0x02
    CMD_STATUS_UPDATE = 0x03
    CMD_START_LOADING = 0x04
    CMD_FINISH_LOADING = 0x05
    CMD_START_UNLOADING = 0x06
    CMD_FINISH_UNLOADING = 0x07
    CMD_ASSIGN_MISSION = 0x08
    CMD_ACK_GATE_OPENED = 0x09
    CMD_FINISH_CHARGING = 0x0A
    CMD_BATTERY = 0x0B
    
    # PC → 트럭 명령어
    CMD_MISSION_ASSIGNED = 0x10
    CMD_NO_MISSION = 0x11
    CMD_RUN = 0x12
    CMD_STOP = 0x13
    CMD_GATE_OPENED = 0x14
    CMD_START_CHARGING = 0x15
    CMD_CANCEL_MISSION = 0x16
    CMD_GATE_CLOSED = 0x17
    
    # 시스템 명령어
    CMD_HELLO = 0xF0
    CMD_HEARTBEAT_ACK = 0xF1
    CMD_HEARTBEAT_CHECK = 0xF2
    
    # sender/receiver IDs
    ID_SERVER = 0x10
    ID_TRUCK_01 = 0x01
    ID_TRUCK_02 = 0x02
    ID_TRUCK_03 = 0x03
    ID_GUI = 0x04
    
    # position 코드
    POS_CHECKPOINT_A = 0x01
    POS_CHECKPOINT_B = 0x02
    POS_CHECKPOINT_C = 0x03
    POS_CHECKPOINT_D = 0x04
    POS_LOAD_A = 0x05
    POS_LOAD_B = 0x06
    POS_BELT = 0x07
    POS_STANDBY = 0x08
    POS_GATE_A = 0xA1
    POS_GATE_B = 0xA2
    POS_UNKNOWN = 0x00
    
    # 상태 코드 (배터리 등)
    STATE_NORMAL = 0x00
    STATE_EMERGENCY = 0x01
    STATE_LOW_BATTERY = 0x02
    STATE_CHARGING = 0x03
    STATE_FULLY_CHARGED = 0x04
    
    # ID 매핑 (문자열 ↔ 바이트)
    ID_MAP = {
        "SERVER": ID_SERVER,
        "TRUCK_01": ID_TRUCK_01,
        "TRUCK_02": ID_TRUCK_02,
        "TRUCK_03": ID_TRUCK_03,
        "GUI": ID_GUI
    }
    
    ID_MAP_REVERSE = {v: k for k, v in ID_MAP.items()}
    
    # 명령어 매핑 (문자열 ↔ 바이트)
    CMD_MAP = {
        "ARRIVED": CMD_ARRIVED,
        "OBSTACLE": CMD_OBSTACLE,
        "STATUS_UPDATE": CMD_STATUS_UPDATE,
        "START_LOADING": CMD_START_LOADING,
        "FINISH_LOADING": CMD_FINISH_LOADING,
        "START_UNLOADING": CMD_START_UNLOADING,
        "FINISH_UNLOADING": CMD_FINISH_UNLOADING,
        "ASSIGN_MISSION": CMD_ASSIGN_MISSION,
        "ACK_GATE_OPENED": CMD_ACK_GATE_OPENED,
        "FINISH_CHARGING": CMD_FINISH_CHARGING,
        "BATTERY": CMD_BATTERY,
        "MISSION_ASSIGNED": CMD_MISSION_ASSIGNED,
        "NO_MISSION": CMD_NO_MISSION,
        "RUN": CMD_RUN,
        "STOP": CMD_STOP,
        "GATE_OPENED": CMD_GATE_OPENED,
        "START_CHARGING": CMD_START_CHARGING,
        "CANCEL_MISSION": CMD_CANCEL_MISSION,
        "GATE_CLOSED": CMD_GATE_CLOSED,
        "HELLO": CMD_HELLO,
        "HEARTBEAT_ACK": CMD_HEARTBEAT_ACK,
        "HEARTBEAT_CHECK": CMD_HEARTBEAT_CHECK
    }
    
    CMD_MAP_REVERSE = {v: k for k, v in CMD_MAP.items()}
    
    # 위치 매핑
    POS_MAP = {
        "CHECKPOINT_A": POS_CHECKPOINT_A,
        "CHECKPOINT_B": POS_CHECKPOINT_B,
        "CHECKPOINT_C": POS_CHECKPOINT_C,
        "CHECKPOINT_D": POS_CHECKPOINT_D,
        "LOAD_A": POS_LOAD_A,
        "LOAD_B": POS_LOAD_B,
        "BELT": POS_BELT,
        "STANDBY": POS_STANDBY,
        "GATE_A": POS_GATE_A,
        "GATE_B": POS_GATE_B,
        "UNKNOWN": POS_UNKNOWN
    }
    
    POS_MAP_REVERSE = {v: k for k, v in POS_MAP.items()}
    
    # 상태 매핑
    STATE_MAP = {
        "NORMAL": STATE_NORMAL,
        "EMERGENCY": STATE_EMERGENCY,
        "LOW_BATTERY": STATE_LOW_BATTERY,
        "CHARGING": STATE_CHARGING,
        "FULLY_CHARGED": STATE_FULLY_CHARGED
    }
    
    STATE_MAP_REVERSE = {v: k for k, v in STATE_MAP.items()}
    
    @staticmethod
    def _get_id_code(id_str):
        return TCPProtocol.ID_MAP.get(id_str, 0)
        
    @staticmethod
    def _get_id_str(id_code):
        return TCPProtocol.ID_MAP_REVERSE.get(id_code, "UNKNOWN")
        
    @staticmethod
    def _get_cmd_code(cmd_str):
        return TCPProtocol.CMD_MAP.get(cmd_str.upper(), 0)
        
    @staticmethod
    def _get_cmd_str(cmd_code):
        return TCPProtocol.CMD_MAP_REVERSE.get(cmd_code, "UNKNOWN")
        
    @staticmethod
    def _get_pos_code(pos_str):
        if pos_str is None:
            return TCPProtocol.POS_UNKNOWN
        return TCPProtocol.POS_MAP.get(pos_str.upper(), TCPProtocol.POS_UNKNOWN)
        
    @staticmethod
    def _get_pos_str(pos_code):
        return TCPProtocol.POS_MAP_REVERSE.get(pos_code, "UNKNOWN")
    
    @staticmethod
    def _get_state_code(state_str):
        if state_str is None:
            return TCPProtocol.STATE_NORMAL
        return TCPProtocol.STATE_MAP.get(state_str.upper(), TCPProtocol.STATE_NORMAL)
        
    @staticmethod
    def _get_state_str(state_code):
        return TCPProtocol.STATE_MAP_REVERSE.get(state_code, "NORMAL")
    
    @staticmethod
    def _encode_payload(cmd_code, payload):
        """명령어에 따라 payload를 바이너리로 인코딩"""
        payload_bytes = b""
        
        # MISSION_ASSIGNED
        if cmd_code == TCPProtocol.CMD_MISSION_ASSIGNED:
            # 단순화: source만 포함
            source = payload.get("source", "LOAD_A")
            source_code = TCPProtocol._get_pos_code(source)
            payload_bytes = bytes([source_code])
            
        # NO_MISSION
        elif cmd_code == TCPProtocol.CMD_NO_MISSION:
            # 선택적 reason 및 wait_time 포함
            reason = payload.get("reason", "NO_MISSIONS_AVAILABLE")
            wait_time = min(255, int(payload.get("wait_time", 10)))
            
            reason_bytes = reason.encode()[:32]  # 최대 32바이트
            reason_len = len(reason_bytes)
            
            # 바이너리 구성: wait_time(1) + reason_len(1) + reason_bytes(가변)
            payload_bytes = bytes([wait_time, reason_len]) + reason_bytes
            
        # GATE_OPENED
        elif cmd_code == TCPProtocol.CMD_GATE_OPENED:
            gate_id = payload.get("gate_id", "GATE_A")
            gate_code = TCPProtocol._get_pos_code(gate_id)
            payload_bytes = bytes([gate_code])
            
        # GATE_CLOSED
        elif cmd_code == TCPProtocol.CMD_GATE_CLOSED:
            gate_id = payload.get("gate_id", "GATE_A")
            gate_code = TCPProtocol._get_pos_code(gate_id)
            payload_bytes = bytes([gate_code])
        
        # ARRIVED
        elif cmd_code == TCPProtocol.CMD_ARRIVED:
            position = payload.get("position", "UNKNOWN")
            position_code = TCPProtocol._get_pos_code(position)
            
            if "gate_id" in payload:
                gate = payload.get("gate_id")
                gate_code = TCPProtocol._get_pos_code(gate)
                payload_bytes = bytes([position_code, gate_code])
            else:
                payload_bytes = bytes([position_code])
        
        # OBSTACLE
        elif cmd_code == TCPProtocol.CMD_OBSTACLE:
            position = payload.get("position", "UNKNOWN")
            position_code = TCPProtocol._get_pos_code(position)
            
            detected = payload.get("detected") == "DETECTED"
            detected_byte = 1 if detected else 0
            
            # 장애물 거리(cm) 추가 - 2바이트 정수로 인코딩
            distance_cm = int(payload.get("distance_cm", 0))
            distance_bytes = struct.pack(">H", distance_cm)  # 빅 엔디안 2바이트 부호 없는 정수
            
            payload_bytes = bytes([position_code, detected_byte]) + distance_bytes
        
        # STATUS_UPDATE
        elif cmd_code == TCPProtocol.CMD_STATUS_UPDATE:
            # 단순화: battery_level, position_code만 포함
            battery_level = min(100, int(payload.get("battery_level", 100)))
            position = payload.get("position", "UNKNOWN")
            position_code = TCPProtocol._get_pos_code(position)
            
            # 바이너리 구성: battery_level(1) + position_code(1)
            payload_bytes = bytes([battery_level, position_code])
        
        # BATTERY 전용 명령어
        elif cmd_code == TCPProtocol.CMD_BATTERY:
            # 배터리 레벨 및 상태 전송
            battery_level = min(100, int(payload.get("battery_level", 100)))
            is_charging = 1 if payload.get("is_charging", False) else 0
            battery_state = int(payload.get("battery_state", 0)) & 0xFF
            
            payload_bytes = bytes([battery_level, is_charging, battery_state])
        
        # ACK_GATE_OPENED
        elif cmd_code == TCPProtocol.CMD_ACK_GATE_OPENED:
            gate = payload.get("gate_id", "GATE_A")
            position = payload.get("position", "UNKNOWN")
            
            gate_code = TCPProtocol._get_pos_code(gate)
            position_code = TCPProtocol._get_pos_code(position)
            
            payload_bytes = bytes([gate_code, position_code])
        
        # START_LOADING, FINISH_LOADING, START_UNLOADING, FINISH_UNLOADING
        elif cmd_code in [TCPProtocol.CMD_START_LOADING, 
                          TCPProtocol.CMD_FINISH_LOADING,
                          TCPProtocol.CMD_START_UNLOADING,
                          TCPProtocol.CMD_FINISH_UNLOADING]:
            # 확장된 위치 검증 - FINISH_LOADING은 특히 중요
            position = "UNKNOWN"
            
            if "position" in payload and payload["position"]:
                position = payload["position"]
                if position == "UNKNOWN" and cmd_code == TCPProtocol.CMD_FINISH_LOADING:
                    position = "LOAD_A"  # FINISH_LOADING이고 위치가 UNKNOWN이면 LOAD_A 사용
            # FINISH_LOADING에 대한 추가 검증
            elif cmd_code == TCPProtocol.CMD_FINISH_LOADING:
                position = "LOAD_A"  # 위치 정보가 없으면 기본값 사용
                print(f"[⚠️ 프로토콜 위치 보정] FINISH_LOADING에 position 필드가 없어 기본값 LOAD_A로 설정")
            
            # 최종 위치 값이 적재 위치인지 확인 (FINISH_LOADING)
            if cmd_code == TCPProtocol.CMD_FINISH_LOADING and position not in ["LOAD_A", "LOAD_B"]:
                print(f"[⚠️ 프로토콜 위치 강제 변경] FINISH_LOADING의 위치가 '{position}'로 부적절하여 'LOAD_A'로 강제 설정")
                position = "LOAD_A"
                
            position_code = TCPProtocol._get_pos_code(position)
            payload_bytes = bytes([position_code])
        
        # CANCEL_MISSION
        elif cmd_code == TCPProtocol.CMD_CANCEL_MISSION:
            # 미션 ID 및 사유 포함
            reason = payload.get("reason", "CANCELED_BY_SERVER")
            
            reason_bytes = reason.encode()[:32]  # 최대 32바이트
            reason_len = len(reason_bytes)
            
            # 바이너리 구성: reason_len(1) + reason_bytes(가변)
            payload_bytes = bytes([reason_len]) + reason_bytes
        
        # FINISH_CHARGING
        elif cmd_code == TCPProtocol.CMD_FINISH_CHARGING:
            # 배터리 레벨 포함
            battery_level = min(100, int(payload.get("battery_level", 100)))
            payload_bytes = bytes([battery_level])
        
        return payload_bytes
    
    @staticmethod
    def _decode_payload(cmd_code, payload_bytes):
        """바이너리 페이로드를 명령어에 따라 디코딩"""
        payload = {}
        
        # MISSION_ASSIGNED
        if cmd_code == TCPProtocol.CMD_MISSION_ASSIGNED and len(payload_bytes) >= 1:
            # 단순화: source만 포함
            source_code = payload_bytes[0]
            source = TCPProtocol._get_pos_str(source_code)
            payload["source"] = source
            
        # NO_MISSION
        elif cmd_code == TCPProtocol.CMD_NO_MISSION and len(payload_bytes) >= 2:
            wait_time = payload_bytes[0]
            reason_len = payload_bytes[1]
            
            payload["wait_time"] = wait_time
            
            # 사유 추출 (있는 경우)
            if len(payload_bytes) >= 2 + reason_len:
                reason = payload_bytes[2:2+reason_len].decode(errors='replace')
                payload["reason"] = reason
            
        # GATE_OPENED
        elif cmd_code == TCPProtocol.CMD_GATE_OPENED and len(payload_bytes) >= 1:
            gate_code = payload_bytes[0]
            gate = TCPProtocol._get_pos_str(gate_code)
            payload["gate_id"] = gate
            
        # GATE_CLOSED
        elif cmd_code == TCPProtocol.CMD_GATE_CLOSED and len(payload_bytes) >= 1:
            gate_code = payload_bytes[0]
            gate = TCPProtocol._get_pos_str(gate_code)
            payload["gate_id"] = gate
        
        # ARRIVED
        elif cmd_code == TCPProtocol.CMD_ARRIVED and len(payload_bytes) >= 1:
            position_code = payload_bytes[0]
            position = TCPProtocol._get_pos_str(position_code)
            payload["position"] = position
            
            # 추가 게이트 정보가 있는 경우
            if len(payload_bytes) >= 2:
                gate_code = payload_bytes[1]
                gate = TCPProtocol._get_pos_str(gate_code)
                payload["gate_id"] = gate
        
        # OBSTACLE
        elif cmd_code == TCPProtocol.CMD_OBSTACLE and len(payload_bytes) >= 2:
            position_code = payload_bytes[0]
            position = TCPProtocol._get_pos_str(position_code)
            detected = payload_bytes[1] != 0
            
            payload["position"] = position
            payload["detected"] = "DETECTED" if detected else "CLEARED"
            
            # 거리 정보가 있는 경우
            if len(payload_bytes) >= 4:
                distance_cm = struct.unpack(">H", payload_bytes[2:4])[0]
                payload["distance_cm"] = distance_cm
        
        # STATUS_UPDATE
        elif cmd_code == TCPProtocol.CMD_STATUS_UPDATE and len(payload_bytes) >= 2:
            # 단순화: battery_level, position_code만 포함
            battery_level = payload_bytes[0]
            position_code = payload_bytes[1]
            position = TCPProtocol._get_pos_str(position_code)
            
            payload["battery_level"] = battery_level
            payload["position"] = position
        
        # BATTERY
        elif cmd_code == TCPProtocol.CMD_BATTERY and len(payload_bytes) >= 3:
            battery_level = payload_bytes[0]
            is_charging = payload_bytes[1] != 0
            battery_state = payload_bytes[2]
            
            payload["battery_level"] = battery_level
            payload["is_charging"] = is_charging
            payload["battery_state"] = battery_state
            
        # START_LOADING, FINISH_LOADING, START_UNLOADING, FINISH_UNLOADING
        elif cmd_code in [TCPProtocol.CMD_START_LOADING, 
                           TCPProtocol.CMD_FINISH_LOADING,
                           TCPProtocol.CMD_START_UNLOADING,
                           TCPProtocol.CMD_FINISH_UNLOADING] and len(payload_bytes) >= 1:
            position_code = payload_bytes[0]
            position = TCPProtocol._get_pos_str(position_code)
            payload["position"] = position
            
        # ACK_GATE_OPENED
        elif cmd_code == TCPProtocol.CMD_ACK_GATE_OPENED and len(payload_bytes) >= 2:
            gate_code = payload_bytes[0]
            position_code = payload_bytes[1]
            
            gate = TCPProtocol._get_pos_str(gate_code)
            position = TCPProtocol._get_pos_str(position_code)
            
            payload["gate_id"] = gate
            payload["position"] = position
        
        # CANCEL_MISSION
        elif cmd_code == TCPProtocol.CMD_CANCEL_MISSION and len(payload_bytes) >= 1:
            reason_len = payload_bytes[0]
            
            # 사유 추출 (있는 경우)
            if len(payload_bytes) >= 1 + reason_len:
                reason = payload_bytes[1:1+reason_len].decode(errors='replace')
                payload["reason"] = reason
            
        # FINISH_CHARGING - 배터리 레벨 추가
        elif cmd_code == TCPProtocol.CMD_FINISH_CHARGING and len(payload_bytes) >= 1:
            battery_level = payload_bytes[0]
            payload["battery_level"] = battery_level
        
        return payload

    @staticmethod
    def build_message(sender, receiver, cmd, payload=None):
        """
        바이너리 메시지 구조 생성:
        - sender_id (1 바이트)
        - receiver_id (1 바이트)
        - cmd_id (1 바이트)
        - payload_len (1 바이트)
        - payload (가변 길이)
        """
        if payload is None:
            payload = {}
            
        # ID와 명령어 코드 변환
        sender_id = TCPProtocol._get_id_code(sender)
        receiver_id = TCPProtocol._get_id_code(receiver)
        cmd_id = TCPProtocol._get_cmd_code(cmd)
        
        # 페이로드 인코딩
        payload_bytes = TCPProtocol._encode_payload(cmd_id, payload)
        payload_len = len(payload_bytes)
        
        # 헤더 (4바이트) + 페이로드
        header = struct.pack("BBBB", sender_id, receiver_id, cmd_id, payload_len)
        return header + payload_bytes
    
    @staticmethod
    def parse_message(raw_data):
        """바이너리 메시지 파싱"""
        try:
            # 최소 메시지 길이 검사 (헤더 4바이트)
            if len(raw_data) < 4:
                return {
                    "type": "INVALID",
                    "error": "Message too short",
                    "raw": raw_data
                }
                
            # 헤더 파싱
            sender_id, receiver_id, cmd_id, payload_len = struct.unpack("BBBB", raw_data[:4])
            
            # ID와 명령어 문자열 변환
            sender = TCPProtocol._get_id_str(sender_id)
            receiver = TCPProtocol._get_id_str(receiver_id)
            cmd = TCPProtocol._get_cmd_str(cmd_id)
            
            # 페이로드 길이 검사
            if len(raw_data) < 4 + payload_len:
                return {
                    "type": "INVALID",
                    "error": "Payload length mismatch",
                    "raw": raw_data
                }
                
            # 페이로드 디코딩
            payload_bytes = raw_data[4:4+payload_len]
            payload = TCPProtocol._decode_payload(cmd_id, payload_bytes)
            
            # 최종 메시지 구조
            return {
                "sender": sender,
                "receiver": receiver,
                "cmd": cmd,
                "payload": payload
            }
            
        except Exception as e:
            return {
                "type": "INVALID",
                "error": str(e),
                "raw": raw_data
            }
