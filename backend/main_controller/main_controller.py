from backend.serialio.port_manager import PortManager
from backend.serialio.belt_controller import BeltController
from backend.serialio.gate_controller import GateController

from backend.mission.mission_db import MissionDB
from backend.mission.mission_manager import MissionManager

from backend.truck_status.truck_status_db import TruckStatusDB
from backend.truck_status.truck_status_manager import TruckStatusManager

from backend.tcpio.truck_commander import TruckCommandSender
from backend.truck_fsm.truck_fsm_manager import TruckFSMManager
from backend.truck_fsm.truck_message_handler import TruckMessageHandler


class MainController:
    def __init__(self, port_map, use_fake=False):
        # Serial 연결
        self.serial_manager = PortManager(port_map, use_fake=use_fake)

        # Mission DB 초기화 (MySQL)
        self.mission_db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.mission_manager = MissionManager(self.mission_db)

        # TruckStatusDB 초기화 (MySQL)
        self.status_db = TruckStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.truck_status_manager = TruckStatusManager(self.status_db)

        # 장치 컨트롤러들 설정
        # 벨트 컨트롤러는 이미 PortManager에서 생성됨
        self.belt_controller = self.serial_manager.controllers.get("BELT")
        
        # 게이트 컨트롤러는 따로 생성
        self.gate_controller = GateController(self.serial_manager)
        
        # FSM 관리자
        self.truck_fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            truck_status_manager=self.truck_status_manager
        )

        # 트럭 메시지 핸들러
        self.truck_message_handler = TruckMessageHandler(self.truck_fsm_manager)
        self.truck_message_handler.set_status_manager(self.truck_status_manager)

        # 초기 TruckCommandSender 설정
        self.set_truck_commander({})

        print("[✅ MainController 초기화 완료]")

    # 트럭 명령 전송자 설정
    def set_truck_commander(self, truck_socket_map: dict):
        """트럭 명령 전송자 설정"""
        commander = TruckCommandSender(truck_socket_map)
        self.truck_fsm_manager.set_commander(commander)

    # 메시지 처리
    def handle_message(self, msg: dict):
        """메시지 처리"""
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()
        payload = msg.get("payload", {})

        print(f"[📨 MainController] sender={sender}, cmd={cmd}")

        # 벨트 수동 제어
        if cmd.startswith("BELT_"):
            self._handle_manual_belt_command(cmd)
            return

        # 게이트 수동 제어
        if cmd.startswith("GATE_"):
            self._handle_manual_gate_command(cmd)
            return

        # 트럭 메시지 처리
        if sender:
            self.truck_message_handler.handle_message(msg)
        else:
            print("[⚠️ 경고] sender가 없는 메시지")

    # 수동 벨트 제어 명령 처리
    def _handle_manual_belt_command(self, cmd: str):
        """수동 벨트 제어"""
        print(f"[⚙️ 수동 벨트 제어] CMD: {cmd}")
        self.belt_controller.handle_message(cmd)

    # 수동 게이트 제어 명령 처리
    def _handle_manual_gate_command(self, cmd: str):
        """수동 게이트 제어"""
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

    # 시스템 종료
    def shutdown(self):
        """시스템 종료"""
        print("[🔌 시스템 종료 중...]")
        self.mission_db.close()
        self.status_db.close()
        self.serial_manager.close_all()
        print("[✅ 시스템 종료 완료]") 