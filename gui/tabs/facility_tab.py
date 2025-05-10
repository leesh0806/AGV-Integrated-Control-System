from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
import os


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
            gate_a_open.clicked.connect(lambda: self.control_gate("A", True))
            
        gate_a_close = self.findChild(QWidget, "pushButton_gate_a_close")
        if gate_a_close:
            gate_a_close.clicked.connect(lambda: self.control_gate("A", False))
            
        gate_b_open = self.findChild(QWidget, "pushButton_gate_b_open")
        if gate_b_open:
            gate_b_open.clicked.connect(lambda: self.control_gate("B", True))
            
        gate_b_close = self.findChild(QWidget, "pushButton_gate_b_close")
        if gate_b_close:
            gate_b_close.clicked.connect(lambda: self.control_gate("B", False))
            
        # 속도 슬라이더 이벤트 연결
        belt_slider = self.findChild(QWidget, "horizontalSlider_belt")
        if belt_slider:
            belt_slider.valueChanged.connect(self.update_belt_speed)
            
    def start_belt(self):
        """벨트 시작"""
        print("[DEBUG] 벨트 시작")
        # TODO: 벨트 컨트롤러와 연동하는 코드 구현
        self.log_facility_action("벨트 시작")
        
    def stop_belt(self):
        """벨트 정지"""
        print("[DEBUG] 벨트 정지")
        # TODO: 벨트 컨트롤러와 연동하는 코드 구현
        self.log_facility_action("벨트 정지")
        
    def emergency_stop_belt(self):
        """벨트 비상 정지"""
        print("[DEBUG] 벨트 비상 정지")
        # TODO: 벨트 컨트롤러와 연동하는 코드 구현
        self.log_facility_action("벨트 비상 정지")
        
    def control_gate(self, gate_id, is_open):
        """게이트 제어"""
        action = "열기" if is_open else "닫기"
        print(f"[DEBUG] 게이트 {gate_id} {action}")
        # TODO: 게이트 컨트롤러와 연동하는 코드 구현
        self.log_facility_action(f"게이트 {gate_id} {action}")
        
    def update_belt_speed(self, value):
        """벨트 속도 업데이트"""
        lcd = self.findChild(QWidget, "lcdNumber_belt")
        if lcd:
            lcd.display(value)
        # TODO: 실제 벨트 속도를 조절하는 코드 구현
        print(f"[DEBUG] 벨트 속도 변경: {value}")
        
    def log_facility_action(self, message):
        """시설 제어 로그 기록"""
        text_edit = self.findChild(QWidget, "textEdit_system_status")
        if text_edit:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_edit.append(f"[{timestamp}] {message}")
            # 항상 마지막 로그가 보이도록 스크롤
            text_edit.verticalScrollBar().setValue(text_edit.verticalScrollBar().maximum()) 