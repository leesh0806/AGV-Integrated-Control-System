# backend/controller/app_controller.py

from serialio.serial_manager import SerialManager
from fsm.gate_controller import GateController
from mission.manager import MissionManager
from fsm.fsm_manager import TruckFSMManager
from mission.db import MissionDB
from fsm.truck_manager import TruckManager
from tcpio.truck_commander import TruckCommandSender


class AppController:
    def __init__(self, port_map, use_fake=False):
        # Serial 연결
        self.serial_manager = SerialManager(port_map, use_fake=use_fake)

        # DB 연결
        self.db = MissionDB(
            host="localhost",
            user='root',
            password='jinhyuk2dacibul',
            database='dust'
        )

        self.gate_controller = GateController(self.serial_manager)
        self.mission_manager = MissionManager(self.db)
        self.mission_manager.load_from_db()
        self.fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager
        )
        self.truck_manager = TruckManager(self.fsm_manager)

    def set_truck_commander(self, truck_socket_map: dict):
        commander = TruckCommandSender(truck_socket_map)
        self.fsm_manager.set_commander(commander)

    def handle_message(self, msg: dict):
        """
        TCP 서버에서 메시지를 수신하면 호출됨.
        """
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()

        print(f"[📨 AppController] sender={sender}, cmd={cmd}")

        # TruckManager에 위임하여 해석 및 FSM 트리거 처리
        self.truck_manager.handle_message(msg)
