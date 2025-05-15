from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QLabel
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6 import uic
import os
from datetime import datetime

# API 클라이언트 가져오기
from gui.api_client import api_client

class MissionTab(QWidget):
    """미션 관리 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_mission.ui")
        print(f"[INFO] 미션 탭 UI 파일 경로: {ui_path}")
        
        if os.path.exists(ui_path):
            print(f"[INFO] 미션 탭 UI 파일 로드 시작: {ui_path}")
            uic.loadUi(ui_path, self)
            print(f"[INFO] 미션 탭 UI 파일 로드 완료")
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 탭 위젯 크기 정책 설정
        self.setMinimumHeight(600)  # 최소 높이 설정
        self.setMinimumWidth(1200)  # 최소 너비 설정
        
        # 출발지 콤보박스가 로드되지 않을 경우 직접 생성
        # self._ensure_source_combo_exists()
        
        # 테이블 설정
        self.setup_table()
        
        # 버튼 이벤트 연결
        self.setup_controls()
        
        # 업데이트 타이머 설정
        self.setup_timer()
        
    def _ensure_source_combo_exists(self):
        """출발지 콤보박스 확인 및 필요시 생성"""
        self.mission_source_combo = self.findChild(QComboBox, "comboBox_new_mission_source")
        
        # 콤보박스가 없으면 새로 생성
        if not self.mission_source_combo:
            print("[경고] UI에서 콤보박스를 찾을 수 없어 직접 생성합니다")
            
            # groupBox가 있는지 확인
            self.groupBox = self.findChild(QWidget, "groupBox")
            if self.groupBox:
                # 콤보박스 생성
                self.mission_source_combo = QComboBox(self.groupBox)
                self.mission_source_combo.setObjectName("comboBox_new_mission_source")
                self.mission_source_combo.setGeometry(960, 60, 141, 27)
                
                # 라벨 생성
                label = QLabel("적재지 선택:", self.groupBox)
                label.setGeometry(960, 40, 91, 19)
                label.show()
            else:
                print("[경고] groupBox를 찾을 수 없어 메인 위젯에 콤보박스를 생성합니다")
                self.mission_source_combo = QComboBox(self)
                self.mission_source_combo.setObjectName("comboBox_new_mission_source")
                self.mission_source_combo.setGeometry(960, 60, 141, 27)
            
            # 콤보박스 내용 설정
            self.mission_source_combo.addItem("적재지 A", "LOAD_A")
            self.mission_source_combo.addItem("적재지 B", "LOAD_B")
            self.mission_source_combo.setCurrentIndex(0)
            self.mission_source_combo.show()
        
        # 콤보박스 항목 설정 (이미 있는 경우에도 설정)
        if self.mission_source_combo:
            self.mission_source_combo.clear()
            self.mission_source_combo.addItem("적재지 A", "LOAD_A")
            self.mission_source_combo.addItem("적재지 B", "LOAD_B")
            self.mission_source_combo.setCurrentIndex(0)
            print("[INFO] 미션 출발지 콤보박스 설정 완료")
        
    def sizeHint(self):
        # 권장 크기 힌트 제공 (Qt 레이아웃 시스템에서 사용)
        return QSize(1200, 600)
        
    def setup_table(self):
        """테이블 위젯 초기화"""
        table = self.tableWidget_mission
        
        # 테이블 헤더 설정
        headers = [
            "ID", 
            "등록 시간", 
            "트럭", 
            "출발지", 
            "목적지", 
            "화물 유형", 
            "수량",
            "상태", 
            "생성 시간"    # 타임스탬프를 생성 시간으로 명확하게 변경
        ]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # 테이블 헤더 스트레치 모드 설정 변경
        # 기존의 Stretch 모드 제거
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # 초기 데이터 로드
        self.refresh_mission_table()
        
        # 컬럼 너비를 테이블 전체 너비 대비 퍼센트로 설정
        self.set_column_widths(table)
        
        # 테이블 크기가 변경될 때 컬럼 너비를 재조정하는 이벤트 연결
        table.resizeEvent = lambda event: self.resize_table_columns(event, table)
    
    def set_column_widths(self, table):
        """테이블 컬럼 너비를 퍼센트 기준으로 설정"""
        width = table.width()
        
        # 각 컬럼의 너비 비율(%) 설정
        column_widths = {
            0: 8,    # ID (8%)
            1: 14,   # 등록 시간 (14%)
            2: 8,    # 트럭 (8%)
            3: 12,   # 출발지 (12%)
            4: 12,   # 목적지 (12%)
            5: 12,   # 화물 유형 (12%)
            6: 6,    # 수량 (6%)
            7: 10,   # 상태 (10%)
            8: 18    # 생성 시간 (18%)
        }
        
        # 컬럼 너비 설정
        for col, percent in column_widths.items():
            if col < table.columnCount():
                pixel_width = int(width * percent / 100)
                table.setColumnWidth(col, pixel_width)
    
    def resize_table_columns(self, event, table):
        """테이블 크기가 변경될 때 컬럼 너비를 재조정"""
        # 컬럼 너비 재설정
        self.set_column_widths(table)
        
        # 이벤트 전파
        if hasattr(QWidget, 'resizeEvent'):
            QWidget.resizeEvent(table, event)
    
    def setup_controls(self):
        """버튼 이벤트 연결"""
        # 미션 출발지 콤보박스 직접 참조 확인
        if hasattr(self, 'mission_source_combo') and self.mission_source_combo:
            print("[INFO] 미션 출발지 콤보박스 사용 준비 완료")
        else:
            print("[경고] setup_controls에서 미션 출발지 콤보박스를 찾을 수 없습니다")
            # 다시 한번 생성 시도
            self._ensure_source_combo_exists()
            
        # 미션 추가 버튼
        add_mission_button = self.findChild(QWidget, "pushButton_add_new_mission")
        if add_mission_button:
            add_mission_button.clicked.connect(self.add_new_mission)
        else:
            print("[경고] 'pushButton_add_new_mission' 버튼을 찾을 수 없습니다")
        
        # 선택한 미션 취소 버튼
        cancel_selected_button = self.findChild(QWidget, "pushButton_cancel_selected")
        if cancel_selected_button:
            cancel_selected_button.clicked.connect(self.cancel_selected_mission)
        else:
            print("[경고] 'pushButton_cancel_selected' 버튼을 찾을 수 없습니다")
        
        # 전체 미션 취소 버튼
        cancel_all_button = self.findChild(QWidget, "pushButton_cancel_all")
        if cancel_all_button:
            cancel_all_button.clicked.connect(self.cancel_all_missions)
        else:
            print("[경고] 'pushButton_cancel_all' 버튼을 찾을 수 없습니다")
        
        # 새로고침 버튼
        refresh_button = self.findChild(QWidget, "pushButton_refresh_table")
        if refresh_button:
            refresh_button.clicked.connect(self.refresh_mission_table)
        else:
            print("[경고] 'pushButton_refresh_table' 버튼을 찾을 수 없습니다")
        
        # 필터 체크박스 이벤트 연결
        checkboxes = [
            self.checkBox_waiting_for_search,
            self.checkBox_assigned_for_search,
            self.checkBox_error_for_search,
            self.checkBox_canceled_for_search,
            self.checkBox_completed_for_search
        ]
        
        for checkbox in checkboxes:
            if checkbox:
                checkbox.stateChanged.connect(self.apply_mission_filters)
            else:
                print(f"[경고] 체크박스를 찾을 수 없습니다: {checkbox}")
        
        # 콤보박스 이벤트 연결
        if hasattr(self, 'comboBox_truck_id_for_search'):
            self.comboBox_truck_id_for_search.currentIndexChanged.connect(self.apply_mission_filters)
        else:
            print("[경고] 'comboBox_truck_id_for_search' 콤보박스를 찾을 수 없습니다")
            
        # 출발지 필터 콤보박스 설정 및 연결
        source_filter_combo = self.findChild(QComboBox, "comboBox_source_for_search")
        if source_filter_combo:
            # 기존 항목을 지우고 한글 항목으로 대체
            source_filter_combo.clear()
            source_filter_combo.addItem("모든 출발지")
            source_filter_combo.addItem("적재지 A", "LOAD_A")
            source_filter_combo.addItem("적재지 B", "LOAD_B")
            
            source_filter_combo.currentIndexChanged.connect(self.apply_mission_filters)
        else:
            print("[경고] 'comboBox_source_for_search' 콤보박스를 찾을 수 없습니다")
            
        # 콤보박스 목록 디버깅
        print("[DEBUG] 사용 가능한 콤보박스 목록:")
        for child in self.findChildren(QComboBox):
            print(f"  - {child.objectName()}")
    
    def setup_timer(self):
        """업데이트 타이머 설정"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_mission_table)
        self.update_timer.start(10000)  # 10초마다 업데이트
    
    def refresh_mission_table(self):
        """미션 테이블 데이터 새로고침"""
        try:
            # API 호출하여 미션 데이터 가져오기
            response = api_client.get_missions()
            
            # API 응답 디버깅
            print("[DEBUG] API 응답 타입:", type(response))
            print("[DEBUG] API 응답 키:", response.keys() if isinstance(response, dict) else "리스트 형식")
            if isinstance(response, dict) and "missions" in response:
                if response["missions"] and isinstance(response["missions"], list) and len(response["missions"]) > 0:
                    first_mission = response["missions"][0]
                    print("[DEBUG] 첫 번째 미션 데이터 구조:", first_mission.keys())
                    print("[DEBUG] 첫 번째 미션 예시:", first_mission)
            
            # 기존 필터 상태 저장
            self.save_filters()
            
            # 테이블 초기화
            self.tableWidget_mission.setRowCount(0)
            
            # 응답 형식 확인 및 처리
            if isinstance(response, dict):
                # 딕셔너리 형태로 반환된 경우
                if not response.get("success", False):
                    print(f"[ERROR] 미션 목록 가져오기 실패: {response.get('message', '알 수 없는 오류')}")
                    return
                
                missions = response.get("missions", {})
                # 미션이 딕셔너리 형태인 경우 값(value)만 추출
                if isinstance(missions, dict):
                    missions = list(missions.values())
            elif isinstance(response, list):
                # 리스트 형태로 직접 반환된 경우
                missions = response
            else:
                print(f"[ERROR] 예상치 못한 응답 형식: {type(response)}")
                return
            
            # 미션 데이터 추가
            for mission in missions:
                if isinstance(mission, dict):  # 미션이 딕셔너리인지 확인
                    self.add_mission_to_table(mission)
                else:
                    print(f"[ERROR] 잘못된 미션 데이터 형식: {type(mission)}")
            
            # 필터 적용
            self.apply_mission_filters()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] 미션 테이블 업데이트 실패: {e}")
    
    def save_filters(self):
        """현재 필터 상태 저장"""
        # 출발지 필터 값 가져오기
        source_filter_combo = self.findChild(QComboBox, "comboBox_source_for_search")
        source_filter = "모든 출발지"
        source_filter_value = None
        
        if source_filter_combo:
            source_filter = source_filter_combo.currentText()
            current_index = source_filter_combo.currentIndex()
            if current_index > 0:
                source_filter_value = source_filter_combo.itemData(current_index)
        
        self.filters = {
            "waiting": self.checkBox_waiting_for_search.isChecked(),
            "assigned": self.checkBox_assigned_for_search.isChecked(),
            "error": self.checkBox_error_for_search.isChecked(),
            "canceled": self.checkBox_canceled_for_search.isChecked(),
            "completed": self.checkBox_completed_for_search.isChecked(),
            "truck": self.comboBox_truck_id_for_search.currentText(),
            "source_display": source_filter,
            "source_value": source_filter_value
        }
    
    def add_mission_to_table(self, mission):
        """테이블에 미션 데이터 추가"""
        table = self.tableWidget_mission
        row = table.rowCount()
        table.insertRow(row)
        
        # 디버깅용 미션 데이터 구조 출력
        if row == 0:  # 첫 번째 미션에 대해서만 출력
            print("[DEBUG] 미션 데이터 구조:")
            print(f"  - 필드: {list(mission.keys())}")
            print(f"  - 예시: {mission}")
            
            # 중첩된 객체 확인
            for key, value in mission.items():
                if isinstance(value, dict):
                    print(f"  - '{key}' 객체 구조: {list(value.keys())}")
                    
            # 타임스탬프 관련 필드 확인
            timestamp_keys = [k for k in mission.keys() if 'time' in k.lower()]
            print(f"  - 타임스탬프 관련 필드: {timestamp_keys}")
        
        # 데이터 매핑
        mission_id = mission.get("mission_id", mission.get("id", ""))  # mission_id 또는 id 필드 사용
        
        # 타임스탬프 필드 처리 - 여러 가능한 필드명 확인
        created_at = (
            mission.get("timestamp_created") or
            mission.get("created_at") or 
            mission.get("created_timestamp") or
            mission.get("creation_time") or
            ""
        )
        
        truck_id = mission.get("assigned_truck_id", mission.get("truck_id", ""))  # assigned_truck_id 또는 truck_id 필드 사용
        source = mission.get("source", "")
        destination = mission.get("destination", "")
        cargo_type = mission.get("cargo_type", "")
        
        # 화물 유형 한글 표시 처리
        cargo_type_display = "기본 화물"
        if cargo_type:
            if cargo_type == "A":
                cargo_type_display = "기본 화물"
            elif cargo_type == "B":
                cargo_type_display = "B형 화물"
            elif cargo_type == "C":
                cargo_type_display = "C형 화물"
        
        # 화물 수량 처리
        quantity = mission.get("cargo_amount", mission.get("quantity", mission.get("cargo_quantity", "")))
        
        # 상태 처리
        if isinstance(mission.get("status"), dict):
            # status가 객체인 경우
            status = mission.get("status", {}).get("code", "")
        else:
            # status가 문자열인 경우
            status = mission.get("status", "")
        
        # 출발지 한글 변환
        source_display = source
        if source == "LOAD_A":
            source_display = "적재지 A"
        elif source == "LOAD_B":
            source_display = "적재지 B"
        
        # 목적지 한글 변환
        destination_display = destination
        if destination == "BELT":
            destination_display = "컨베이어 벨트"
        
        # 생성 시간 형식 변환
        created_at_formatted = created_at
        try:
            if created_at:
                # ISO 형식의 날짜 문자열 처리 (Z가 있는 경우 타임존 정보 추가)
                if isinstance(created_at, str) and ('T' in created_at or ':' in created_at):
                    created_at_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at_formatted = created_at_obj.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError, TypeError) as e:
            print(f"[ERROR] 날짜 형식 변환 실패: {e}, 원본값: {created_at}")
            created_at_formatted = str(created_at) if created_at else "-"
        
        # 상태 텍스트 변환
        status_text = {
            "WAITING": "대기 중",
            "ASSIGNED": "할당됨",
            "IN_PROGRESS": "진행 중",
            "COMPLETED": "완료됨",
            "CANCELED": "취소됨",
            "ERROR": "오류"
        }.get(status, status)
        
        # 테이블에 데이터 추가
        items = [
            mission_id,
            created_at_formatted,
            truck_id,
            source_display,
            destination_display,
            cargo_type_display,        # 화물 유형 한글 표시
            str(quantity),             # 화물 수량 (문자열로 변환)
            status_text,
            created_at_formatted       # 생성 시간 표시
        ]
        
        for col, text in enumerate(items):
            item = QTableWidgetItem(str(text))
            # ID 열은 사용자 데이터로 저장 (정렬용)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, mission_id)
            # 출발지 열은 원본 데이터도 저장 (필터링용)
            elif col == 3:
                item.setData(Qt.ItemDataRole.UserRole, source)
            table.setItem(row, col, item)
            
        # 상태에 따른 행 색상 설정
        if status == "ERROR":
            for col in range(table.columnCount()):
                table.item(row, col).setBackground(Qt.GlobalColor.red)
        elif status == "COMPLETED":
            for col in range(table.columnCount()):
                table.item(row, col).setBackground(Qt.GlobalColor.green)
        elif status == "CANCELED":
            for col in range(table.columnCount()):
                table.item(row, col).setForeground(Qt.GlobalColor.gray)
    
    def apply_mission_filters(self):
        """테이블에 필터 적용"""
        table = self.tableWidget_mission
        
        # 필터 상태 가져오기
        show_waiting = self.checkBox_waiting_for_search.isChecked()
        show_assigned = self.checkBox_assigned_for_search.isChecked()
        show_error = self.checkBox_error_for_search.isChecked()
        show_canceled = self.checkBox_canceled_for_search.isChecked()
        show_completed = self.checkBox_completed_for_search.isChecked()
        
        truck_filter = self.comboBox_truck_id_for_search.currentText()
        
        # 출발지 필터 가져오기
        source_filter_combo = self.findChild(QComboBox, "comboBox_source_for_search")
        source_filter = "모든 출발지"
        source_filter_value = None
        
        if source_filter_combo:
            source_filter = source_filter_combo.currentText()
            current_index = source_filter_combo.currentIndex()
            if current_index > 0:  # 0번 항목이 아닌 경우 (첫 번째 항목은 "모든 출발지")
                source_filter_value = source_filter_combo.itemData(current_index)
        
        # 각 행에 대해 필터 적용
        for row in range(table.rowCount()):
            # 상태 확인
            status = table.item(row, 7).text()
            show_by_status = (
                (status == "대기 중" and show_waiting) or
                (status == "할당됨" and show_assigned) or
                (status == "진행 중" and show_assigned) or  # 진행 중은 할당됨 필터에 포함
                (status == "오류" and show_error) or
                (status == "취소됨" and show_canceled) or
                (status == "완료됨" and show_completed)
            )
            
            # 트럭 필터 확인
            truck = table.item(row, 2).text()
            show_by_truck = truck_filter == "모든 트럭" or truck == truck_filter
            
            # 출발지 필터 확인
            source_item = table.item(row, 3)
            source_display = source_item.text()  # 테이블에 표시된 출발지 (한글)
            
            if source_filter == "모든 출발지":
                show_by_source = True
            elif source_filter_value:
                # 내부 데이터로 비교 (LOAD_A, LOAD_B)
                source_data = source_item.data(Qt.ItemDataRole.UserRole)
                show_by_source = source_data == source_filter_value
            else:
                # 텍스트로 비교 (적재지 A, 적재지 B)
                show_by_source = source_display == source_filter
            
            # 모든 조건이 충족되면 행 표시, 아니면 숨김
            table.setRowHidden(row, not (show_by_status and show_by_truck and show_by_source))
    
    def open_add_mission_dialog(self):
        """미션 추가 다이얼로그 표시 (레거시 메서드, 기본적으로 add_new_mission으로 대체)"""
        self.add_new_mission()
    
    def cancel_selected_mission(self):
        """선택된 미션 취소"""
        try:
            table = self.tableWidget_mission
            selected_rows = table.selectionModel().selectedRows()
            
            if not selected_rows:
                QMessageBox.warning(self, "미션 취소", "취소할 미션을 선택해주세요.")
                return
            
            # 첫 번째 선택된 행의 미션 ID 가져오기
            row = selected_rows[0].row()
            mission_id = table.item(row, 0).text()
            
            # 확인 대화상자
            reply = QMessageBox.question(
                self,
                "미션 취소",
                f"미션 ID: {mission_id}를 취소하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # API 호출
                response = api_client.cancel_mission(mission_id)
                
                if response.get("success", False):
                    QMessageBox.information(self, "미션 취소 성공", f"미션 ID: {mission_id}가 취소되었습니다.")
                    # 테이블 새로고침
                    self.refresh_mission_table()
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    QMessageBox.warning(self, "미션 취소 실패", error_msg)
        except Exception as e:
            print(f"[ERROR] 미션 취소 실패: {e}")
            QMessageBox.critical(self, "오류", f"미션 취소 실패: {e}")
    
    def add_new_mission(self):
        """새 미션 추가 (UI에서 직접)"""
        try:
            # 새 미션의 출발지 가져오기
            source = "LOAD_A"  # 기본값 설정
            display_text = "적재지 A"  # 기본 표시 텍스트
            
            # 멤버 변수에 저장된 콤보박스 사용
            if hasattr(self, 'mission_source_combo') and self.mission_source_combo:
                source_combo = self.mission_source_combo
                
                if source_combo.count() > 0:
                    # 현재 선택된 항목의 데이터 값 가져오기
                    current_index = source_combo.currentIndex()
                    variant_data = source_combo.itemData(current_index)
                    
                    if variant_data is not None:
                        source = str(variant_data)
                    
                    # 디스플레이 텍스트 가져오기
                    display_text = source_combo.currentText()
                    print(f"[INFO] 선택된 출발지: {display_text} (값: {source})")
            else:
                print("[경고] 출발지 콤보박스를 찾을 수 없습니다. 기본값 사용: LOAD_A")
                
            # 목적지는 항상 BELT로 설정
            destination = "BELT"
            
            # 트럭은 자동 선택으로 설정 (서버에서 결정)
            truck_id = None
            
            # 화물 종류는 기본 화물로 설정
            cargo_type = "A"  # 기본 화물
            
            # 화물 수량은 기본값 1로 설정
            cargo_amount = 1
            
            try:
                # API 호출
                print(f"[INFO] 미션 생성 요청: source={source}, destination={destination}, cargo_type={cargo_type}, cargo_amount={cargo_amount}")
                response = api_client.create_mission(
                    truck_id=truck_id,
                    source=source,
                    destination=destination,
                    cargo_type=cargo_type,
                    cargo_amount=cargo_amount
                )
                
                print(f"[INFO] API 응답: {response}")
                
                if isinstance(response, dict) and response.get("success", False):
                    mission_id = response.get("mission_id", "알 수 없음")
                    QMessageBox.information(self, "미션 추가 성공", 
                                            f"미션이 성공적으로 등록되었습니다.\n"
                                            f"ID: {mission_id}\n"
                                            f"출발지: {display_text}\n"
                                            f"화물 유형: 기본 화물")
                    # 테이블 새로고침
                    self.refresh_mission_table()
                else:
                    error_msg = "알 수 없는 오류"
                    if isinstance(response, dict):
                        error_msg = response.get("message", error_msg)
                    QMessageBox.warning(self, "미션 추가 실패", error_msg)
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "오류", f"미션 등록 중 오류 발생: {e}")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] 미션 추가 실패: {e}")
            QMessageBox.critical(self, "오류", f"미션 추가 실패: {e}")
            
    def cancel_all_missions(self):
        """모든 미션 취소"""
        try:
            # 확인 대화상자
            reply = QMessageBox.question(
                self,
                "모든 미션 취소",
                "모든 미션을 취소하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 테이블에서 모든 미션 ID 가져오기
                mission_ids = []
                table = self.tableWidget_mission
                
                for row in range(table.rowCount()):
                    mission_id = table.item(row, 0).text()
                    # 상태 확인 (완료된 미션은 취소하지 않음)
                    status = table.item(row, 7).text()
                    if status not in ["완료됨", "취소됨"]:
                        mission_ids.append(mission_id)
                
                if not mission_ids:
                    QMessageBox.information(self, "알림", "취소할 미션이 없습니다.")
                    return
                    
                # 모든 미션 취소 요청
                success_count = 0
                error_count = 0
                for mission_id in mission_ids:
                    try:
                        response = api_client.cancel_mission(mission_id)
                        if response.get("success", False):
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1
                
                # 결과 메시지
                result_msg = f"총 {len(mission_ids)}개의 미션 중 {success_count}개 취소 성공, {error_count}개 실패"
                QMessageBox.information(self, "미션 취소 결과", result_msg)
                
                # 테이블 새로고침
                self.refresh_mission_table()
                
        except Exception as e:
            print(f"[ERROR] 모든 미션 취소 실패: {e}")
            QMessageBox.critical(self, "오류", f"모든 미션 취소 실패: {e}") 