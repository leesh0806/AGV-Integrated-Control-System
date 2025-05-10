from PyQt6.QtWidgets import QWidget, QMessageBox, QScrollBar
from PyQt6 import uic
import os
from gui.api_client import api_client


class FacilityTab(QWidget):
    """시설 제어 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_facility.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 초기화
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        # 벨트 제어 버튼 이벤트 연결
        belt_start = self.findChild(QWidget, "pushButton_belt_start")
        if belt_start:
            belt_start.clicked.connect(self.start_belt)
            
        belt_stop = self.findChild(QWidget, "pushButton_belt_stop")
        if belt_stop:
            belt_stop.clicked.connect(self.stop_belt)
            
        belt_emergency = self.findChild(QWidget, "pushButton_belt_emergency")
        if belt_emergency:
            belt_emergency.clicked.connect(self.emergency_stop_belt)
            
        # 게이트 제어 버튼 이벤트 연결
        gate_a_open = self.findChild(QWidget, "pushButton_gate_a_open")
        if gate_a_open:
            gate_a_open.clicked.connect(lambda: self.control_gate("GATE_A", "open"))
            
        gate_a_close = self.findChild(QWidget, "pushButton_gate_a_close")
        if gate_a_close:
            gate_a_close.clicked.connect(lambda: self.control_gate("GATE_A", "close"))
            
        gate_b_open = self.findChild(QWidget, "pushButton_gate_b_open")
        if gate_b_open:
            gate_b_open.clicked.connect(lambda: self.control_gate("GATE_B", "open"))
            
        gate_b_close = self.findChild(QWidget, "pushButton_gate_b_close")
        if gate_b_close:
            gate_b_close.clicked.connect(lambda: self.control_gate("GATE_B", "close"))
            
        # 속도 슬라이더 이벤트 연결
        belt_slider = self.findChild(QWidget, "horizontalSlider_belt")
        if belt_slider:
            belt_slider.valueChanged.connect(self.update_belt_speed)
            
    def get_belt_speed(self):
        """슬라이더에서 벨트 속도 가져오기"""
        belt_slider = self.findChild(QWidget, "horizontalSlider_belt")
        if belt_slider:
            return belt_slider.value()
        return 50  # 기본값
        
    def start_belt(self):
        """벨트 시작"""
        try:
            speed = self.get_belt_speed()
            response = api_client.control_belt("BELT", "start", speed)
            self.log_facility_action(f"벨트 시작 (속도: {speed})")
            print(f"[INFO] 벨트 시작 (속도: {speed})")
        except Exception as e:
            error_msg = f"벨트 시작 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
        
    def stop_belt(self):
        """벨트 정지"""
        try:
            response = api_client.control_belt("BELT", "stop")
            self.log_facility_action("벨트 정지")
            print("[INFO] 벨트 정지")
        except Exception as e:
            error_msg = f"벨트 정지 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
        
    def emergency_stop_belt(self):
        """벨트 비상 정지"""
        try:
            response = api_client.control_belt("BELT", "emergency_stop")
            self.log_facility_action("벨트 비상 정지")
            print("[INFO] 벨트 비상 정지")
        except Exception as e:
            error_msg = f"벨트 비상 정지 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
        
    def control_gate(self, gate_id, command):
        """게이트 제어"""
        try:
            response = api_client.control_gate(gate_id, command)
            action = "열기" if command == "open" else "닫기"
            self.log_facility_action(f"게이트 {gate_id} {action}")
            print(f"[INFO] 게이트 {gate_id} {action}")
        except Exception as e:
            error_msg = f"게이트 {gate_id} 제어 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
        
    def update_belt_speed(self, value):
        """벨트 속도 업데이트"""
        lcd = self.findChild(QWidget, "lcdNumber_belt")
        if lcd:
            lcd.display(value)
            
        # 벨트가 이미 실행 중인 경우에만 속도 업데이트 요청
        try:
            belt_status = api_client.get_belt("BELT")
            if belt_status.get("status") == "running":
                response = api_client.control_belt("BELT", "set_speed", value)
                self.log_facility_action(f"벨트 속도 변경: {value}")
                print(f"[INFO] 벨트 속도 변경: {value}")
        except Exception as e:
            # 실패해도 메시지 상자는 표시하지 않고 로그만 남김
            print(f"[ERROR] 벨트 속도 업데이트 실패: {e}")
        
    def log_facility_action(self, message):
        """시설 제어 로그 기록"""
        text_edit = self.findChild(QWidget, "textEdit_system_status")
        if text_edit:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_edit.append(f"[{timestamp}] {message}")
            
            # 항상 마지막 로그가 보이도록 스크롤
            scroll_bar = text_edit.verticalScrollBar()
            if scroll_bar:
                scroll_bar.setValue(scroll_bar.maximum()) 