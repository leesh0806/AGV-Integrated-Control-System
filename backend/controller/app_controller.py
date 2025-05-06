# backend/controller/app_controller.py

from backend.serialio.serial_manager import SerialManager
from backend.serialio.belt_controller import BeltController
from backend.serialio.gate_controller import GateController

from backend.mission.db import MissionDB
from backend.mission.manager import MissionManager
from backend.mission.mission import Mission

from backend.fsm.fsm_manager import TruckFSMManager
from backend.fsm.truck_manager import TruckManager

from backend.tcpio.truck_commander import TruckCommandSender
from backend.api.truck_status_api import set_truck_position

from backend.battery.db import BatteryDB
from backend.battery.manager import BatteryManager


class AppController:
    def __init__(self, port_map, use_fake=False):
        # ✅ Serial 연결
        self.serial_manager = SerialManager(port_map, use_fake=use_fake)

        # ✅ DB 연결
        self.db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )

        # ✅ 배터리 DB 및 매니저 초기화
        self.battery_db = BatteryDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.battery_manager = BatteryManager(self.battery_db)

        # ✅ 장치 컨트롤러들
        self.belt_controller = BeltController(self.serial_manager.controllers["BELT"])
        self.gate_controller = GateController(self.serial_manager)

        # ✅ 미션 및 FSM 관리자
        self.mission_manager = MissionManager(self.db)
        self.mission_manager.load_from_db()  # DB에서 미션 로드

        self.fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            battery_manager=self.battery_manager
        )

        self.truck_manager = TruckManager(self.fsm_manager)
        self.truck_manager.set_battery_manager(self.battery_manager)  # 배터리 매니저 설정

        # ✅ 초기 TruckCommandSender 설정
        self.set_truck_commander({})

        self.truck_positions = {}

    def set_truck_commander(self, truck_socket_map: dict):
        """
        서버에서 소켓 맵을 넘겨줬을 때 TruckCommandSender 초기화
        """
        commander = TruckCommandSender(truck_socket_map)
        self.fsm_manager.set_commander(commander)

    def handle_message(self, msg: dict):
        """
        TCP 서버로부터 메시지를 수신했을 때 호출됨.
        :param msg: {"sender": "GUI", "cmd": "BELTACT", ...}
        """
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()

        print(f"[📨 AppController] sender={sender}, cmd={cmd}")

        # ✅ 1. 벨트 디버깅/수동 제어 명령
        if self._is_manual_belt_command(cmd):
            self._handle_manual_belt_command(cmd)
            return

        # ✅ 2. 게이트 수동 제어 명령 (예: "GATE_A_OPEN")
        if cmd.startswith("GATE_"):
            self._handle_manual_gate_command(cmd)
            return

        # 트럭 위치 ARRIVED 명령 처리
        if cmd == "ARRIVED":
            position = msg.get("payload", {}).get("position")
            if sender and position:
                self.truck_positions[sender] = position.upper()
                set_truck_position(sender, position.upper())  # Flask API와 동기화
            # ★ 반드시 트럭 FSM에도 메시지 전달
            self.truck_manager.handle_message(msg)
            return

        # ✅ 3. 트럭 FSM 관련 명령
        self.truck_manager.handle_message(msg)

    # ─────────────────────────────────────────────

    def _is_manual_belt_command(self, cmd: str) -> bool:
        return cmd in {"BELTACT", "BELTOFF", "EMRSTOP", "A_FULL"}

    def _handle_manual_belt_command(self, cmd: str):
        print(f"[⚙️ 수동 벨트 제어] CMD: {cmd}")
        self.belt_controller.handle_message(cmd)

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
