from PyQt6.QtWidgets import QMainWindow, QTableWidgetItem, QWidget, QVBoxLayout
from PyQt6 import uic
import os
from backend.mission.db import MissionDB
from backend.mission.manager import MissionManager
from backend.mission.mission import Mission
from datetime import datetime
from gui.ui.main_monitoring_tab import MainMonitoringTab

class MainTabWindow(QMainWindow):
    def __init__(self, role=None):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "test_tab.ui")
        uic.loadUi(ui_path, self)
        self.setWindowTitle("지능형 운송관제 시스템 D.U.S.T.")
        # --- graphicsview_map만 MainMonitoringTab으로 교체 ---
        parent = self.tab_main_monitoring
        old = parent.findChild(QWidget, "graphicsview_map")
        layout = parent.layout()
        if layout is None:
            layout = QVBoxLayout(parent)
            parent.setLayout(layout)
        if old is not None:
            idx = layout.indexOf(old)
            layout.removeWidget(old)
            old.setParent(None)
            self.monitoring_tab = MainMonitoringTab(parent)
            layout.insertWidget(idx, self.monitoring_tab)
        # --- 이하 기존 코드 ---
        # DB 및 미션 매니저 초기화
        self.mission_db = MissionDB(host="localhost", user="root", password="jinhyuk2dacibul", database="dust")
        self.mission_manager = MissionManager(self.mission_db)
        self.mission_manager.load_from_db()
        # 테이블 헤더 설정 (실제 의미 있는 정보만)
        self.tablewidget.setColumnCount(10)
        self.tablewidget.setHorizontalHeaderLabels([
            "미션ID", "화물종류", "수량", "출발지", "도착지", "상태", "트럭ID", "생성시각", "배정시각", "완료시각"
        ])
        self.refresh_mission_table()
        # 버튼 이벤트 연결
        self.pushbutton_add.clicked.connect(self.add_mission)
        self.pushbutton_delete.clicked.connect(self.delete_selected_mission)
        self.pushbutton_refresh.clicked.connect(self.refresh_button_clicked)
        # combobox_source에 출발지 옵션 추가
        self.combobox_source.clear()
        self.combobox_source.addItems(["load_A", "load_B"])

    def refresh_mission_table(self):
        self.tablewidget.setRowCount(0)
        missions = list(self.mission_manager.waiting_queue) + list(self.mission_manager.active_missions.values())
        for mission in missions:
            row = self.tablewidget.rowCount()
            self.tablewidget.insertRow(row)
            self.tablewidget.setItem(row, 0, QTableWidgetItem(mission.mission_id))
            self.tablewidget.setItem(row, 1, QTableWidgetItem(mission.cargo_type))
            self.tablewidget.setItem(row, 2, QTableWidgetItem(str(mission.cargo_amount)))
            self.tablewidget.setItem(row, 3, QTableWidgetItem(mission.source))
            self.tablewidget.setItem(row, 4, QTableWidgetItem(mission.destination))
            self.tablewidget.setItem(row, 5, QTableWidgetItem(mission.status.value))  # 한글 라벨만 표시
            self.tablewidget.setItem(row, 6, QTableWidgetItem(str(mission.assigned_truck_id)))
            self.tablewidget.setItem(row, 7, QTableWidgetItem(str(mission.timestamp_created)))
            self.tablewidget.setItem(row, 8, QTableWidgetItem(str(mission.timestamp_assigned)))
            self.tablewidget.setItem(row, 9, QTableWidgetItem(str(mission.timestamp_completed)))

    def add_mission(self):
        # mission_id를 자동 생성
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        mission_id = f"mission_{now}"
        cargo_type = self.lineedit_type.text()
        cargo_amount = self.spinBox.value()
        source = self.combobox_source.currentText()
        destination = "belt"  # 도착지는 belt로 고정
        truck_id = "TRUCK_01" # 트럭ID 고정
        mission = Mission(mission_id, cargo_type, cargo_amount, source, destination, truck_id=truck_id)
        self.mission_manager.add_mission(mission)
        self.refresh_mission_table()

    def delete_selected_mission(self):
        selected = self.tablewidget.currentRow()
        if selected < 0:
            return
        mission_id = self.tablewidget.item(selected, 0).text()
        self.mission_manager.cancel_mission(mission_id)
        self.refresh_mission_table()

    def refresh_button_clicked(self):
        self.mission_manager.waiting_queue.clear()
        self.mission_manager.active_missions.clear()
        self.mission_manager.load_from_db()
        self.refresh_mission_table() 