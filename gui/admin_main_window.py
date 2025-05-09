from PyQt6.QtWidgets import QMainWindow, QTableWidgetItem, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer
from PyQt6 import uic

from backend.mission.mission_db import MissionDB
from backend.mission.mission_manager import MissionManager
from backend.mission.mission import Mission
from backend.mission.mission_status import MissionStatus

from gui.ui.main_monitoring_tab import MainMonitoringTab

from datetime import datetime
import os, requests


class AdminMainWindow(QMainWindow):
    def __init__(self, role=None):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "main.ui")
        uic.loadUi(ui_path, self)
        self.setWindowTitle("지능형 운송관제 시스템 D.U.S.T.")

        # --------------------------------------------------------

        # Main Monitoring Tab

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

        self.battery_timer = QTimer()
        self.battery_timer.timeout.connect(self.refresh_battery_status)
        self.battery_timer.start(1000)

        # --------------------------------------------------------

        # Mission Management Tab

        # DB 및 미션 매니저 초기화
        self.mission_db = MissionDB(host="localhost", user="root", password="jinhyuk2dacibul", database="dust")
        self.mission_manager = MissionManager(self.mission_db)

        # 테이블 헤더 설정 (실제 의미 있는 정보만)
        self.tablewidget.setColumnCount(11)
        self.tablewidget.setHorizontalHeaderLabels([
            "미션ID", "화물종류", "수량", "출발지", "도착지", "상태코드", "상태설명", "트럭ID", "생성시각", "배정시각", "완료시각"
        ])
        self.refresh_mission_table()

        # 버튼 이벤트 연결
        self.pushbutton_add.clicked.connect(self.add_mission)
        self.pushbutton_delete.clicked.connect(self.delete_selected_mission)
        self.pushbutton_refresh.clicked.connect(self.refresh_button_clicked)

        # combobox_source에 출발지 옵션 추가
        self.combobox_source.clear()
        self.combobox_source.addItems(["load_A", "load_B"])

        # --------------------------------------------------------

        # Truck Management Tab

        # --------------------------------------------------------

        # Facility Management Tab

        # --------------------------------------------------------

        # Settings Tab

        # --------------------------------------------------------


    def refresh_mission_table(self):
        self.tablewidget.setRowCount(0)
        
        # API로 미션 데이터 가져오기
        try:
            response = requests.get("http://127.0.0.1:5001/api/missions")
            if response.status_code == 200:
                missions = response.json()
                
                for mission in missions:
                    row_idx = self.tablewidget.rowCount()
                    self.tablewidget.insertRow(row_idx)
                    
                    # 기본 정보 표시
                    self.tablewidget.setItem(row_idx, 0, QTableWidgetItem(str(mission.get('mission_id', ''))))
                    self.tablewidget.setItem(row_idx, 1, QTableWidgetItem(str(mission.get('cargo_type', ''))))
                    self.tablewidget.setItem(row_idx, 2, QTableWidgetItem(str(mission.get('cargo_amount', ''))))
                    self.tablewidget.setItem(row_idx, 3, QTableWidgetItem(str(mission.get('source', ''))))
                    self.tablewidget.setItem(row_idx, 4, QTableWidgetItem(str(mission.get('destination', ''))))
                    
                    # 상태 처리
                    status = mission.get('status', {})
                    status_code = ''
                    status_label = ''
                    
                    if isinstance(status, dict):
                        status_code = status.get('code', '')
                        status_label = status.get('label', '')
                    elif isinstance(status, str):
                        status_code = status
                    else:
                        status_code = str(status)
                    
                    self.tablewidget.setItem(row_idx, 5, QTableWidgetItem(status_code))
                    if status_label:
                        self.tablewidget.setItem(row_idx, 6, QTableWidgetItem(status_label))
                    
                    # 나머지 정보 표시
                    self.tablewidget.setItem(row_idx, 7, QTableWidgetItem(str(mission.get('assigned_truck_id', ''))))
                    self.tablewidget.setItem(row_idx, 8, QTableWidgetItem(str(mission.get('timestamp_created', ''))))
                    self.tablewidget.setItem(row_idx, 9, QTableWidgetItem(str(mission.get('timestamp_assigned', ''))))
                    self.tablewidget.setItem(row_idx, 10, QTableWidgetItem(str(mission.get('timestamp_completed', ''))))
                
                return
            
        except Exception as e:
            print(f"[ERROR] API에서 미션 정보를 가져오는 중 오류 발생: {e}")
            # API 호출 실패 시 기존 방식으로 DB에서 직접 가져옴
        
        # 기존 방식: DB에서 직접 가져오기
        mission_db = MissionDB(host="localhost", user="root", password="jinhyuk2dacibul", database="dust")
        missions = mission_db.get_assigned_and_waiting_missions()
        
        for mission in missions:
            row_idx = self.tablewidget.rowCount()
            self.tablewidget.insertRow(row_idx)
            
            # 딕셔너리 형식으로 가져온 경우 (DB에서 직접 가져옴)
            if isinstance(mission, dict):
                self.tablewidget.setItem(row_idx, 0, QTableWidgetItem(str(mission.get('mission_id', ''))))
                self.tablewidget.setItem(row_idx, 1, QTableWidgetItem(str(mission.get('cargo_type', ''))))
                self.tablewidget.setItem(row_idx, 2, QTableWidgetItem(str(mission.get('cargo_amount', ''))))
                self.tablewidget.setItem(row_idx, 3, QTableWidgetItem(str(mission.get('source', ''))))
                self.tablewidget.setItem(row_idx, 4, QTableWidgetItem(str(mission.get('destination', ''))))
                
                # DB에서는 status_code와 status_label 필드로 분리되어 있음
                self.tablewidget.setItem(row_idx, 5, QTableWidgetItem(str(mission.get('status_code', ''))))
                self.tablewidget.setItem(row_idx, 6, QTableWidgetItem(str(mission.get('status_label', ''))))
                
                self.tablewidget.setItem(row_idx, 7, QTableWidgetItem(str(mission.get('assigned_truck_id', ''))))
                self.tablewidget.setItem(row_idx, 8, QTableWidgetItem(str(mission.get('timestamp_created', ''))))
                self.tablewidget.setItem(row_idx, 9, QTableWidgetItem(str(mission.get('timestamp_assigned', ''))))
                self.tablewidget.setItem(row_idx, 10, QTableWidgetItem(str(mission.get('timestamp_completed', ''))))
            else:
                # Mission 객체인 경우 (이전 코드)
                self.tablewidget.setItem(row_idx, 0, QTableWidgetItem(mission.mission_id))
                self.tablewidget.setItem(row_idx, 1, QTableWidgetItem(mission.cargo_type))
                self.tablewidget.setItem(row_idx, 2, QTableWidgetItem(str(mission.cargo_amount)))
                self.tablewidget.setItem(row_idx, 3, QTableWidgetItem(mission.source))
                self.tablewidget.setItem(row_idx, 4, QTableWidgetItem(mission.destination))
                self.tablewidget.setItem(row_idx, 5, QTableWidgetItem(mission.status.name))
                self.tablewidget.setItem(row_idx, 6, QTableWidgetItem(mission.status.value))
                self.tablewidget.setItem(row_idx, 7, QTableWidgetItem(str(mission.assigned_truck_id)))
                self.tablewidget.setItem(row_idx, 8, QTableWidgetItem(str(mission.timestamp_created)))
                self.tablewidget.setItem(row_idx, 9, QTableWidgetItem(str(mission.timestamp_assigned)))
                self.tablewidget.setItem(row_idx, 10, QTableWidgetItem(str(mission.timestamp_completed)))
                
        mission_db.close()

    def add_mission(self):
        # mission_id를 더 짧은 포맷으로 자동 생성 (예: mission_YYMMDD_HHMMSS)
        now = datetime.now().strftime("%y%m%d_%H%M%S")
        mission_id = f"mission_{now}"
        cargo_type = self.lineedit_type.text()
        cargo_amount = self.spinBox.value()
        source = self.combobox_source.currentText()
        destination = "belt"  # 도착지는 belt로 고정
        
        # 미션 생성
        self.mission_manager.create_mission(
            mission_id=mission_id,
            cargo_type=cargo_type,
            cargo_amount=cargo_amount,
            source=source,
            destination=destination
        )
        self.refresh_mission_table()

    def delete_selected_mission(self):
        selected = self.tablewidget.currentRow()
        if selected < 0:
            return
        mission_id = self.tablewidget.item(selected, 0).text()
        self.mission_manager.cancel_mission(mission_id)
        self.refresh_mission_table()

    def refresh_button_clicked(self):
        self.refresh_mission_table() 

    def refresh_battery_status(self):
        try:
            response = requests.get("http://127.0.0.1:5001/api/truck_battery")
            data = response.json()
            print(f"[DEBUG] 배터리 데이터 수신: {data}")
            
            def update_battery_bar(progress_bar, truck_data, truck_id):
                if not truck_data:  # 데이터가 없는 경우
                    print(f"[DEBUG] 트럭 데이터 없음: {truck_data}")
                    # 기본값 설정 - 등록되지 않은 트럭은 회색으로 표시
                    level = 0
                    is_charging = False
                    color = "#999999"  # 회색
                    
                    # 스타일시트 설정
                    style = f"""
                        QProgressBar {{
                            border: 2px solid grey;
                            border-radius: 5px;
                            text-align: center;
                            background-color: #f0f0f0;
                        }}
                        QProgressBar::chunk {{
                            background-color: {color};
                            width: 10px;
                            margin: 0.5px;
                        }}
                    """
                    progress_bar.setStyleSheet(style)
                    progress_bar.setValue(level)
                    # 트럭 미등록 표시 추가
                    progress_bar.setFormat(f"{truck_id} (미등록)")
                    return
                    
                level = int(truck_data.get("level", 100))
                is_charging = truck_data.get("is_charging", False)
                print(f"[DEBUG] 배터리 레벨: {level}%, 충전중: {is_charging}")
                
                # 배터리 레벨에 따른 색상 설정
                if level <= 30:
                    color = "#FF0000"  # 빨간색 (위험)
                elif level <= 50:
                    color = "#FFA500"  # 주황색 (경고)
                else:
                    color = "#00FF00"  # 초록색 (정상)
                
                # 충전 중일 때는 파란색으로 표시
                if is_charging:
                    color = "#0000FF"  # 파란색
                
                # 스타일시트 설정
                style = f"""
                    QProgressBar {{
                        border: 2px solid grey;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #f0f0f0;
                    }}
                    QProgressBar::chunk {{
                        background-color: {color};
                        width: 10px;
                        margin: 0.5px;
                    }}
                """
                progress_bar.setStyleSheet(style)
                progress_bar.setValue(level)
                # 기본 형식으로 복원
                progress_bar.setFormat("%p%")
                print(f"[DEBUG] 프로그레스바 업데이트: {level}% (스타일: {style})")
            
            # TRUCK_01 배터리 상태 업데이트
            truck1_data = data.get("TRUCK_01", {})
            update_battery_bar(self.progressbar_battery_truck1, truck1_data, "TRUCK_01")
            
            # TRUCK_02 배터리 상태 업데이트
            truck2_data = data.get("TRUCK_02", {})
            update_battery_bar(self.progressbar_battery_truck2, truck2_data, "TRUCK_02")
            
            # TRUCK_03 배터리 상태 업데이트
            truck3_data = data.get("TRUCK_03", {})
            update_battery_bar(self.progressbar_battery_truck3, truck3_data, "TRUCK_03")
            
        except Exception as e:
            print(f"[ERROR] 배터리 상태 업데이트 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()  # 상세한 오류 정보 출력
