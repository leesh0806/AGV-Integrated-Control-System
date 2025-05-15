from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, QTimer, QDate, QSize
from PyQt6 import uic
import os
from datetime import datetime, timedelta

# API 클라이언트 가져오기
from gui.api_client import api_client

class EventLogTab(QWidget):
    """이벤트 로그 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_event_log.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 탭 위젯 크기 정책 설정
        self.setMinimumHeight(600)  # 최소 높이 설정
        self.setMinimumWidth(1200)  # 최소 너비 설정
        
        # 날짜 위젯 초기화
        self.setup_date_widgets()
        
        # 테이블 설정
        self.setup_table()
        
        # 버튼 이벤트 연결
        self.setup_controls()
        
        # 초기 데이터 로드
        self.refresh_log_table()
        
    def sizeHint(self):
        # 권장 크기 힌트 제공 (Qt 레이아웃 시스템에서 사용)
        return QSize(1200, 600)
        
    def setup_date_widgets(self):
        """날짜 위젯 초기화"""
        # 오늘 날짜
        today = QDate.currentDate()
        
        # 시작 날짜 (7일 전)
        start_date = today.addDays(-7)
        
        # 날짜 설정
        self.dateEdit_start.setDate(start_date)
        self.dateEdit_end.setDate(today)
        
    def setup_table(self):
        """테이블 위젯 초기화"""
        table = self.tableWidget_log
        
        # 테이블 헤더 설정 확인
        if table.columnCount() != 4:
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["시간", "로그 레벨", "소스", "메시지"])
        
        # 헤더 크기 조정
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 시간
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 로그 레벨
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 소스
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 메시지
        
        # 행 클릭 이벤트 연결
        table.itemSelectionChanged.connect(self.show_selected_log_detail)
        
    def setup_controls(self):
        """버튼 이벤트 연결"""
        # 필터 적용 버튼
        apply_filter_button = self.pushButton_apply_filter
        if apply_filter_button:
            apply_filter_button.clicked.connect(self.refresh_log_table)
        
        # 새로고침 버튼
        refresh_button = self.pushButton_refresh_log
        if refresh_button:
            refresh_button.clicked.connect(self.refresh_log_table)
        
        # 내보내기 버튼
        export_button = self.pushButton_export_log
        if export_button:
            export_button.clicked.connect(self.export_logs)
        
        # 로그 지우기 버튼
        clear_button = self.pushButton_clear_log
        if clear_button:
            clear_button.clicked.connect(self.clear_logs)
        
    def refresh_log_table(self):
        """로그 테이블 데이터 새로고침"""
        try:
            # 필터 값 가져오기
            start_date = self.dateEdit_start.date().toString(Qt.DateFormat.ISODate)
            end_date = self.dateEdit_end.date().toString(Qt.DateFormat.ISODate)
            
            # end_date에 하루를 더해서 해당 날짜까지 포함되도록 함
            end_date_obj = datetime.fromisoformat(end_date)
            end_date_obj = end_date_obj + timedelta(days=1)
            end_date = end_date_obj.strftime("%Y-%m-%d")
            
            log_level = self.comboBox_log_level.currentText()
            source = self.comboBox_source.currentText()
            keyword = self.lineEdit_keyword.text()
            
            # 로그 레벨 맵핑
            log_level_map = {
                "모든 로그": None,
                "정보": "INFO",
                "경고": "WARNING",
                "오류": "ERROR",
                "긴급": "CRITICAL"
            }
            
            # 소스 맵핑
            source_map = {
                "모든 소스": None,
                "시스템": "SYSTEM",
                "네트워크": "NETWORK",
                "트럭 제어": "TRUCK_CONTROL",
                "미션 관리": "MISSION_MANAGEMENT",
                "사용자 인증": "USER_AUTH"
            }
            
            # API 호출을 위한 필터 준비
            filters = {
                "start_date": start_date,
                "end_date": end_date
            }
            
            # 선택적 필터 추가
            if log_level in log_level_map and log_level_map[log_level]:
                filters["level"] = log_level_map[log_level]
                
            if source in source_map and source_map[source]:
                filters["source"] = source_map[source]
                
            if keyword:
                filters["keyword"] = keyword
            
            # API 호출
            response = api_client.get_logs(filters)
            
            if not response.get("success", False):
                print(f"[ERROR] 로그 데이터 가져오기 실패: {response.get('message', '알 수 없는 오류')}")
                return
            
            # 테이블 초기화
            table = self.tableWidget_log
            table.setRowCount(0)
            
            # 로그 데이터 추가
            logs = response.get("logs", [])
            for log in logs:
                self.add_log_to_table(log)
            
            # 로그 개수 표시
            log_count = table.rowCount()
            self.label_count.setText(f"총 {log_count}개의 로그")
            
        except Exception as e:
            print(f"[ERROR] 로그 테이블 업데이트 실패: {e}")
            QMessageBox.critical(self, "오류", f"로그 데이터 불러오기 실패: {e}")
    
    def add_log_to_table(self, log):
        """테이블에 로그 데이터 추가"""
        table = self.tableWidget_log
        row = table.rowCount()
        table.insertRow(row)
        
        # 데이터 매핑
        timestamp = log.get("timestamp", "")
        level = log.get("level", "")
        source = log.get("source", "")
        message = log.get("message", "")
        
        # 날짜 형식 변환
        try:
            timestamp_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp_formatted = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            timestamp_formatted = timestamp
        
        # 로그 레벨 한글화
        level_text = {
            "INFO": "정보",
            "WARNING": "경고",
            "ERROR": "오류",
            "CRITICAL": "긴급"
        }.get(level, level)
        
        # 소스 한글화
        source_text = {
            "SYSTEM": "시스템",
            "NETWORK": "네트워크",
            "TRUCK_CONTROL": "트럭 제어",
            "MISSION_MANAGEMENT": "미션 관리",
            "USER_AUTH": "사용자 인증"
        }.get(source, source)
        
        # 테이블에 데이터 추가
        items = [
            timestamp_formatted,
            level_text,
            source_text,
            message
        ]
        
        for col, text in enumerate(items):
            item = QTableWidgetItem(str(text))
            # 타임스탬프는 사용자 데이터로 원본 저장 (정렬용)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, timestamp)
            table.setItem(row, col, item)
            
    def show_selected_log_detail(self):
        """선택된 로그의 상세 정보 표시"""
        table = self.tableWidget_log
        selected_indexes = table.selectedIndexes()
        
        if not selected_indexes:
            return
            
        # 동일한 행에서 선택된 항목 처리
        row = selected_indexes[0].row()
        
        # 선택된 로그 데이터 가져오기
        timestamp = table.item(row, 0).text()
        level = table.item(row, 1).text()
        source = table.item(row, 2).text()
        message = table.item(row, 3).text()
        
        # 상세 정보 구성
        detail_text = f"[{timestamp}] [{level}] [{source}]\n{message}"
        
        # 상세 정보를 label_count에 표시 (기존 UI에 존재하는 위젯 활용)
        self.label_count.setText(f"선택된 로그: {timestamp} - {level} - {source}")
    
    def export_logs(self):
        """로그 내보내기"""
        try:
            # 테이블에 표시된 로그 데이터 가져오기
            table = self.tableWidget_log
            row_count = table.rowCount()
            
            if row_count == 0:
                QMessageBox.warning(self, "내보내기 실패", "내보낼 로그 데이터가 없습니다.")
                return
            
            # 저장 파일 위치 선택
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "로그 파일 저장",
                f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV 파일 (*.csv);;모든 파일 (*.*)"
            )
            
            if not file_path:
                return
            
            # CSV 파일 작성
            with open(file_path, 'w', encoding='utf-8') as f:
                # 헤더 작성
                headers = ["시간", "로그 레벨", "소스", "메시지"]
                f.write(','.join(f'"{header}"' for header in headers) + '\n')
                
                # 데이터 작성
                for row in range(row_count):
                    row_data = []
                    for col in range(table.columnCount()):
                        text = table.item(row, col).text().replace('"', '""')  # CSV에서 큰따옴표 처리
                        row_data.append(f'"{text}"')
                    f.write(','.join(row_data) + '\n')
            
            QMessageBox.information(self, "내보내기 성공", f"로그가 {file_path}에 저장되었습니다.")
            
        except Exception as e:
            print(f"[ERROR] 로그 내보내기 실패: {e}")
            QMessageBox.critical(self, "내보내기 오류", f"로그 내보내기 중 오류 발생: {e}")
    
    def clear_logs(self):
        """로그 지우기"""
        try:
            # 확인 대화상자
            reply = QMessageBox.question(
                self,
                "로그 지우기",
                "현재 필터에 표시된 모든 로그를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 필터 값 가져오기
            start_date = self.dateEdit_start.date().toString(Qt.DateFormat.ISODate)
            end_date = self.dateEdit_end.date().toString(Qt.DateFormat.ISODate)
            
            # end_date에 하루를 더해서 해당 날짜까지 포함되도록 함
            end_date_obj = datetime.fromisoformat(end_date)
            end_date_obj = end_date_obj + timedelta(days=1)
            end_date = end_date_obj.strftime("%Y-%m-%d")
            
            log_level = self.comboBox_log_level.currentText()
            source = self.comboBox_source.currentText()
            
            # 로그 레벨 맵핑
            log_level_map = {
                "모든 로그": None,
                "정보": "INFO",
                "경고": "WARNING",
                "오류": "ERROR",
                "긴급": "CRITICAL"
            }
            
            # 소스 맵핑
            source_map = {
                "모든 소스": None,
                "시스템": "SYSTEM",
                "네트워크": "NETWORK",
                "트럭 제어": "TRUCK_CONTROL",
                "미션 관리": "MISSION_MANAGEMENT",
                "사용자 인증": "USER_AUTH"
            }
            
            # API 호출을 위한 필터 준비
            filters = {
                "start_date": start_date,
                "end_date": end_date
            }
            
            # 선택적 필터 추가
            if log_level in log_level_map and log_level_map[log_level]:
                filters["level"] = log_level_map[log_level]
                
            if source in source_map and source_map[source]:
                filters["source"] = source_map[source]
            
            # API 호출
            response = api_client.clear_logs(filters)
            
            if response.get("success", False):
                deleted_count = response.get("deleted_count", 0)
                QMessageBox.information(self, "로그 삭제 성공", f"{deleted_count}개의 로그가 삭제되었습니다.")
                # 테이블 새로고침
                self.refresh_log_table()
            else:
                error_msg = response.get("message", "알 수 없는 오류")
                QMessageBox.warning(self, "로그 삭제 실패", error_msg)
                
        except Exception as e:
            print(f"[ERROR] 로그 삭제 실패: {e}")
            QMessageBox.critical(self, "오류", f"로그 삭제 중 오류 발생: {e}") 