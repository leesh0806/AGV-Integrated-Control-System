from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QComboBox, QLineEdit, QSpinBox, QRadioButton, QButtonGroup, QLabel, QVBoxLayout, QMessageBox
from PyQt6.QtCore import QRect
from PyQt6 import uic
import os
from gui.api_client import api_client


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
            
        # 초기화
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        # 미션 추가 버튼 이벤트 연결
        add_button = self.findChild(QWidget, "pushbutton_add")
        if add_button:
            add_button.clicked.connect(self.add_mission)
        else:
            print("[경고] 'pushbutton_add' 버튼을 찾을 수 없습니다")
        
        # 미션 새로고침 버튼 이벤트 연결
        refresh_button = self.findChild(QWidget, "pushbutton_refresh")
        if refresh_button:
            refresh_button.clicked.connect(self.refresh_mission_table)
        else:
            print("[경고] 'pushbutton_refresh' 버튼을 찾을 수 없습니다")
            
        # 미션 삭제 버튼 이벤트 연결
        delete_button = self.findChild(QWidget, "pushbutton_delete")
        if delete_button:
            delete_button.clicked.connect(self.delete_selected_mission)
        else:
            print("[경고] 'pushbutton_delete' 버튼을 찾을 수 없습니다")
            
        # 미션 테이블 참조
        self.tablewidget = self.findChild(QWidget, "tablewidget")
        
        # 디버깅: 테이블 위젯 존재 여부 확인
        if not self.tablewidget:
            print("[경고] 'tablewidget' 테이블을 찾을 수 없습니다")
            # UI에 있는 모든 위젯 이름 출력
            for child in self.findChildren(QWidget):
                if hasattr(child, 'objectName'):
                    print(f"[디버그] 발견된 위젯: {child.objectName()}")
        else:
            print("[정보] 테이블 위젯을 찾았습니다")
            
        # 미션 테이블 설정
        if self.tablewidget:
            # 테이블 헤더 설정
            self.tablewidget.setColumnCount(11)
            self.tablewidget.setHorizontalHeaderLabels([
                "미션 ID", "화물 종류", "화물 양", "출발지", "목적지", 
                "상태 코드", "상태 레이블", "할당 트럭", "생성 시간", "할당 시간", "완료 시간"
            ])
            
            # 초기 데이터 로드
            self.refresh_mission_table()
            
    def refresh_mission_table(self):
        """미션 테이블 데이터 갱신"""
        if not hasattr(self, 'tablewidget') or not self.tablewidget:
            print("[오류] 테이블 위젯이 없어 미션 데이터를 표시할 수 없습니다")
            return
            
        self.tablewidget.setRowCount(0)
        
        # API로 미션 데이터 가져오기
        try:
            missions = api_client.get_all_missions()
            print(f"[정보] API에서 {len(missions)}개의 미션을 가져왔습니다")
            
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
                
        except Exception as e:
            print(f"[ERROR] 미션 정보를 가져오는 중 오류 발생: {e}")
            QMessageBox.critical(self, "오류", f"미션 정보를 가져오는 중 오류가 발생했습니다: {e}")
            
    def add_mission(self):
        """새 미션 추가"""
        try:
            # 미션 입력값 가져오기 - UI 파일의 위젯 이름 사용
            lineedit_type = self.findChild(QWidget, "lineedit_type")
            if not lineedit_type:
                print("[경고] 'lineedit_type' 필드를 찾을 수 없습니다")
                cargo_type = "기본 화물"
            else:
                cargo_type = lineedit_type.text() or "기본 화물"
                
            spinBox = self.findChild(QWidget, "spinBox")
            if not spinBox:
                print("[경고] 'spinBox' 스핀박스를 찾을 수 없습니다")
                cargo_amount = 1.0
            else:
                cargo_amount = float(spinBox.value())
                
            source_widget = self.findChild(QWidget, "combobox_source")
            if not source_widget:
                print("[경고] 'combobox_source' 콤보박스를 찾을 수 없습니다")
                source = "LOAD_A"
            else:
                source = source_widget.currentText()
                
            # 목적지는 UI에 없으므로 하드코딩
            destination = "BELT"
            
            # 미션 ID 생성 (UI에는 없으므로 현재 시간 기반으로 생성)
            from datetime import datetime
            mission_id = f"MISSION_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 입력값 검증
            if not cargo_type or cargo_amount <= 0 or not source or not destination:
                QMessageBox.warning(self, "입력 오류", "모든 필드를 올바르게 입력해주세요.")
                return
                
            if source == destination:
                QMessageBox.warning(self, "입력 오류", "출발지와 목적지가 같을 수 없습니다.")
                return
                
            # 미션 데이터 생성
            mission_data = {
                "mission_id": mission_id,
                "cargo_type": cargo_type,
                "cargo_amount": cargo_amount,
                "source": source,
                "destination": destination
            }
            
            print(f"[정보] 미션 생성 시도: {mission_data}")
            
            # API로 미션 생성
            response = api_client.create_mission(mission_data)
            
            # 성공 메시지 표시
            QMessageBox.information(self, "미션 생성", f"미션 {mission_id}이(가) 성공적으로 생성되었습니다.")
            
            # 미션 테이블 갱신
            self.refresh_mission_table()
            
            # 입력 필드 초기화
            if lineedit_type:
                lineedit_type.clear()
                
            if spinBox:
                spinBox.setValue(1)
            
        except Exception as e:
            print(f"[ERROR] 미션 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "오류", f"미션 생성 중 오류가 발생했습니다: {e}")
            
    def delete_selected_mission(self):
        """선택된 미션 삭제"""
        if not self.tablewidget:
            print("[오류] 테이블 위젯이 없어 미션을 삭제할 수 없습니다")
            return
            
        # 선택된 행 가져오기
        selected_rows = self.tablewidget.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "선택 오류", "삭제할 미션을 선택해주세요.")
            return
            
        # 선택된 행의 미션 ID 가져오기
        mission_id_items = [self.tablewidget.item(item.row(), 0) for item in selected_rows]
        unique_mission_ids = list(set([item.text() for item in mission_id_items if item is not None]))
        
        if not unique_mission_ids:
            QMessageBox.warning(self, "선택 오류", "삭제할 미션을 선택해주세요.")
            return
            
        # 삭제 확인 메시지 표시
        if len(unique_mission_ids) == 1:
            msg = f"미션 '{unique_mission_ids[0]}'을(를) 취소하시겠습니까?"
        else:
            msg = f"{len(unique_mission_ids)}개의 미션을 취소하시겠습니까?"
            
        reply = QMessageBox.question(self, "미션 취소", msg, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 선택된 미션 취소
            for mission_id in unique_mission_ids:
                try:
                    api_client.cancel_mission(mission_id)
                    print(f"[INFO] 미션 취소: {mission_id}")
                except Exception as e:
                    print(f"[ERROR] 미션 취소 중 오류 발생: {e}")
                    QMessageBox.critical(self, "오류", f"미션 '{mission_id}' 취소 중 오류가 발생했습니다: {e}")
            
            # 미션 테이블 갱신
            self.refresh_mission_table()
            QMessageBox.information(self, "미션 취소", "선택한 미션이 취소되었습니다.") 