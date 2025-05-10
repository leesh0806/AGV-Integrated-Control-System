from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QComboBox, QLineEdit, QSpinBox, QRadioButton, QButtonGroup, QLabel, QVBoxLayout
from PyQt6.QtCore import QRect
from PyQt6 import uic
import os
import requests
from datetime import datetime

from backend.mission.mission_db import MissionDB
from backend.mission.mission_manager import MissionManager


class MissionTab(QWidget):
    """미션 관리 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_mission.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 미션 DB 및 매니저 초기화
        self.mission_db = MissionDB(host="localhost", user="root", password="jinhyuk2dacibul", database="dust")
        self.mission_manager = MissionManager(self.mission_db)
        
        # 초기화
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        # 테이블 위젯 참조
        self.tablewidget = self.findChild(QWidget, "tablewidget")
        if self.tablewidget:
            # 테이블 헤더 설정
            self.tablewidget.setColumnCount(11)
            self.tablewidget.setHorizontalHeaderLabels([
                "미션ID", "화물종류", "수량", "출발지", "도착지", "상태코드", "상태설명", "트럭ID", "생성시각", "배정시각", "완료시각"
            ])
            self.refresh_mission_table()

        # 버튼 이벤트 연결
        self.pushbutton_add = self.findChild(QWidget, "pushbutton_add")
        if self.pushbutton_add:
            self.pushbutton_add.clicked.connect(self.add_mission)
        
        self.pushbutton_delete = self.findChild(QWidget, "pushbutton_delete")
        if self.pushbutton_delete:
            self.pushbutton_delete.clicked.connect(self.delete_selected_mission)
        
        self.pushbutton_refresh = self.findChild(QWidget, "pushbutton_refresh") 
        if self.pushbutton_refresh:
            self.pushbutton_refresh.clicked.connect(self.refresh_button_clicked)

        # 위젯 참조
        self.lineedit_type = self.findChild(QLineEdit, "lineedit_type")
        self.spinBox = self.findChild(QSpinBox, "spinBox")
        self.combobox_source = self.findChild(QComboBox, "combobox_source")
        
        # UI에서 콤보박스 아이템이 이미 설정되어 있으므로 확인만 수행
        if self.combobox_source:
            print(f"[✅ 콤보박스 설정 확인] 아이템 수: {self.combobox_source.count()}개")
            for i in range(self.combobox_source.count()):
                print(f"  - 아이템 {i}: {self.combobox_source.itemText(i)}")
        else:
            print("[❌ 오류] combobox_source를 찾을 수 없습니다")
        
    def refresh_mission_table(self):
        """미션 테이블 데이터 갱신"""
        if not hasattr(self, 'tablewidget') or not self.tablewidget:
            return
            
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
        """새 미션 추가"""
        if not hasattr(self, 'lineedit_type') or not self.lineedit_type:
            print("[❌ 오류] lineedit_type 위젯을 찾을 수 없습니다")
            return
            
        if not hasattr(self, 'combobox_source') or not self.combobox_source:
            print("[❌ 오류] combobox_source 위젯을 찾을 수 없습니다")
            return
            
        # mission_id를 더 짧은 포맷으로 자동 생성 (예: mission_YYMMDD_HHMMSS)
        now = datetime.now().strftime("%y%m%d_%H%M%S")
        mission_id = f"mission_{now}"
        cargo_type = self.lineedit_type.text()
        cargo_amount = self.spinBox.value()
        
        # 콤보박스에서 선택된 값 가져오기
        source = self.combobox_source.currentText()
        if not source:
            # 기본값 설정 (이제는 발생하지 않아야 함)
            source = "LOAD_A"
            print("[⚠️ 경고] source 값이 비어있습니다. 기본값 'LOAD_A'를 사용합니다")
        
        print(f"[📝 미션 생성] ID={mission_id}, 화물={cargo_type}, 수량={cargo_amount}, 출발지={source}")
        
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
        """선택한 미션 삭제"""
        if not hasattr(self, 'tablewidget') or not self.tablewidget:
            return
            
        selected = self.tablewidget.currentRow()
        if selected < 0:
            return
        mission_id = self.tablewidget.item(selected, 0).text()
        self.mission_manager.cancel_mission(mission_id)
        self.refresh_mission_table()

    def refresh_button_clicked(self):
        """미션 테이블 새로고침 버튼 클릭 이벤트"""
        self.refresh_mission_table() 