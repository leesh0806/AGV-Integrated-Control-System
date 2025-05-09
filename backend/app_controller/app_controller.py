# backend/controller/app_controller.py

from backend.serialio.port_manager import PortManager
from backend.serialio.belt_controller import BeltController
from backend.serialio.gate_controller import GateController

from backend.mission.mission_db import MissionDB
from backend.mission.mission_manager import MissionManager

from backend.tcpio.truck_commander import TruckCommandSender

from backend.truck_status.truck_state_manager import TruckStatusManager
from backend.truck_status.db import TruckStatusDB

from backend.truck_fsm.truck_state_enum import TruckState
from backend.truck_fsm.truck_fsm_manager import TruckFSMManager
from backend.truck_fsm.truck_message_handler import TruckMessageHandler


class AppController:
    def __init__(self, port_map, use_fake=False):
        # Serial 연결
        self.serial_manager = PortManager(port_map, use_fake=use_fake)

        # Mission DB 초기화
        self.mission_db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.mission_manager = MissionManager(self.mission_db)

        # TruckStatusDB 초기화
        self.status_db = TruckStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.truck_status_manager = TruckStatusManager(self.status_db)

        # 장치 컨트롤러들
        self.belt_controller = BeltController(self.serial_manager.controllers["BELT"])
        self.gate_controller = GateController(self.serial_manager)
        
        # FSM 관리자
        self.truck_fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            status_manager=self.truck_status_manager
        )

        # 트럭 메시지 핸들러
        self.truck_message_handler = TruckMessageHandler(truck_fsm_manager=self.truck_fsm_manager)
        self.truck_message_handler.set_status_manager(truck_status_manager=self.truck_status_manager)

        # 초기 TruckCommandSender 설정
        self.set_truck_commander({})

    # 트럭 명령 전송자 설정
    def set_truck_commander(self, truck_socket_map: dict):
        commander = TruckCommandSender(truck_socket_map)
        self.truck_fsm_manager.set_commander(commander)

    # 메시지 처리
    def handle_message(self, msg: dict):
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()
        payload = msg.get("payload", {})

        print(f"[📨 AppController] sender={sender}, cmd={cmd}")

        # 1. 벨트 디버깅/수동 제어 명령
        if cmd.startswith("BELT_"):
            self._handle_manual_belt_command(cmd)
            return

        # 2. 게이트 수동 제어 명령
        if cmd.startswith("GATE_"):
            self._handle_manual_gate_command(cmd)
            return

        # 3. 트럭 관련 명령 처리
        if sender:
            self.truck_message_handler.handle_message(msg)
        else:
            print("[⚠️ 경고] sender가 없는 메시지")

    # ─────────────────────────────────────────────
        return cmd in {"BELTACT", "BELTOFF", "EMRSTOP", "A_FULL"}

    # 수동 벨트 제어 명령 처리
    def _handle_manual_belt_command(self, cmd: str):
        print(f"[⚙️ 수동 벨트 제어] CMD: {cmd}")
        self.belt_controller.handle_message(cmd)

    # 수동 게이트 제어 명령 처리
    def _handle_manual_gate_command(self, cmd: str):
        parts = cmd.split("_")
        if len(parts) == 3:
            gate_id = f"GATE_{parts[1]}"
            action = parts[2]
            if action == "OPEN":
                self.gate_controller.open_gate(gate_id)
            elif action == "CLOSE":
                self.gate_controller.close_gate(gate_id)
        else:
            print(f"[❌ 게이트 명령 포맷 오류] {cmd}")
