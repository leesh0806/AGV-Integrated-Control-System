from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QGridLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6 import uic
import os
import math

# 공통 API 클라이언트 가져오기
from gui.api_client import api_client

# 트럭 아이콘 클래스 직접 포함
from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap

# 클릭 가능한 시설물 클래스 정의
class ClickableFacilityItem:
    """클릭 가능한 시설물 아이템 (Rect 또는 Ellipse)"""
    def __init__(self, scene, shape_type, x, y, w, h, facility_id, color, label_text, parent_tab):
        self.facility_id = facility_id
        self.parent_tab = parent_tab
        self.label_text = label_text
        
        # 시설물 형태에 따라 다른 그래픽 아이템 생성
        if shape_type == "ellipse":
            self.shape_item = QGraphicsEllipseItem(x - w / 2, y - h / 2, w, h)
        else:  # "rect"
            self.shape_item = QGraphicsRectItem(x - w / 2, y - h / 2, w, h)
            
        # 스타일 설정
        self.shape_item.setBrush(QBrush(color))
        self.shape_item.setPen(QPen(QColor("black"), 2))
        
        # 클릭 이벤트를 위한 플래그 설정
        self.shape_item.setAcceptHoverEvents(True)
        self.shape_item.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # 커스텀 데이터 저장
        self.shape_item.setData(Qt.ItemDataRole.UserRole, facility_id)
        
        # 씬에 추가
        scene.addItem(self.shape_item)
        
        # 클릭 이벤트 연결을 위한 클래스 패치
        original_mousePressEvent = self.shape_item.mousePressEvent
        
        def mousePressEvent(event):
            # 원래 이벤트 처리 먼저 호출
            if original_mousePressEvent:
                original_mousePressEvent(event)
            # 시설물 제어 다이얼로그 표시
            self.parent_tab.show_facility_control_dialog(self.facility_id, self.label_text)
            event.accept()
            
        # 클래스 메서드 오버라이드
        self.shape_item.mousePressEvent = mousePressEvent
        
        # 호버 효과를 위한 이벤트 처리
        original_hoverEnterEvent = self.shape_item.hoverEnterEvent
        original_hoverLeaveEvent = self.shape_item.hoverLeaveEvent
        
        def hoverEnterEvent(event):
            if original_hoverEnterEvent:
                original_hoverEnterEvent(event)
            # 호버 시 테두리 변경
            self.shape_item.setPen(QPen(QColor("yellow"), 3))
            # 커서 변경
            self.shape_item.setCursor(Qt.CursorShape.PointingHandCursor)
            event.accept()
            
        def hoverLeaveEvent(event):
            if original_hoverLeaveEvent:
                original_hoverLeaveEvent(event)
            # 호버 해제 시 테두리 원래대로
            self.shape_item.setPen(QPen(QColor("black"), 2))
            event.accept()
            
        # 클래스 메서드 오버라이드
        self.shape_item.hoverEnterEvent = hoverEnterEvent
        self.shape_item.hoverLeaveEvent = hoverLeaveEvent

class TruckIcon(QGraphicsPixmapItem):
    def __init__(self, truck_id, parent=None):
        super().__init__(parent)
        self.truck_id = truck_id
        # 트럭 아이콘 이미지 로드 (나중에 실제 이미지로 교체 필요)
        self.setPixmap(QPixmap("gui/assets/truck.png").scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio))
        self.setOffset(-15, -15)  # 아이콘의 중심점을 기준으로 위치 조정
        
    def update_position(self, x, y):
        """트럭의 위치를 업데이트합니다."""
        self.setPos(x, y)


class MonitoringTab(QWidget):
    """메인 모니터링 탭 클래스 - MainMonitoringTab과 통합"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_monitoring.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 탭 위젯 크기 정책 설정
        self.setMinimumHeight(600)  # 최소 높이 설정
        self.setMinimumWidth(1200)  # 최소 너비 설정
        
        # 시설물 맵 객체 저장용 딕셔너리
        self.facility_items = {}
            
        # 초기화
        self.setup_map()
        self.setup_truck()
        self.setup_controls()
        self.setup_timer()
        
    def sizeHint(self):
        # 권장 크기 힌트 제공 (Qt 레이아웃 시스템에서 사용)
        return QSize(1200, 600)
        
    def setup_map(self):
        """맵 초기화 (사각형 레이아웃)"""
        # 씬 생성
        self.scene = QGraphicsScene(self)
        self.graphicsView_map.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 800, 400)  # 맵 크기 조정
        
        # 모서리가 둥근 사각형 맵 좌표 계산용 변수
        left, top = 0, 80        # 좌상단 좌표 (이전 -100에서 150 오른쪽으로 이동)
        right, bottom = 600, 320   # 우하단 좌표 (이전 500에서 150 오른쪽으로 이동)
        width, height = right - left, bottom - top  # 맵 너비, 높이
        
        # 노드 위치 정의 (사각형 레이아웃)
        self.node_coords = {
            # 하단 경로 (왼쪽에서 오른쪽)
            "STANDBY": (left + width * 0.1, bottom),     # 좌측 하단 시작점
            "CHECKPOINT_A": (left + width * 0.3, bottom),
            "GATE_A": (left + width * 0.5, bottom),
            "CHECKPOINT_B": (left + width * 0.7, bottom),
            
            # 우측 경로 (아래에서 위로)
            "B_LOAD": (right, bottom - height * 0.3),    # 우측 하단
            "A_LOAD": (right, top + height * 0.3),       # 우측 상단
            
            # 상단 경로 (오른쪽에서 왼쪽)
            "CHECKPOINT_C": (left + width * 0.7, top),
            "GATE_B": (left + width * 0.5, top),
            "CHECKPOINT_D": (left + width * 0.3, top),
            
            # 좌측 경로 (위에서 아래로)
            "BELT": (left, top + height * 0.3)           # 좌측 상단
        }

        # 사각형 경로 그리기 (모서리가 둥근 형태)
        path = QPainterPath()
        corner_radius = 40  # 모서리 반경
        
        # 경로 그리기 시작 - 좌측 하단에서 시작
        path.moveTo(left + corner_radius, bottom)  # 하단 좌측 모서리 오른쪽에서 시작
        
        # 하단 선
        path.lineTo(right - corner_radius, bottom)  # 하단 우측 모서리 왼쪽까지
        
        # 우측 하단 모서리 (둥근 부분)
        path.arcTo(right - 2*corner_radius, bottom - 2*corner_radius, 2*corner_radius, 2*corner_radius, 270, 90)
        
        # 우측 선
        path.lineTo(right, top + corner_radius)  # 우측 상단 모서리 아래까지
        
        # 우측 상단 모서리 (둥근 부분)
        path.arcTo(right - 2*corner_radius, top, 2*corner_radius, 2*corner_radius, 0, 90)
        
        # 상단 선
        path.lineTo(left + corner_radius, top)  # 상단 좌측 모서리 오른쪽까지
        
        # 좌측 상단 모서리 (둥근 부분)
        path.arcTo(left, top, 2*corner_radius, 2*corner_radius, 90, 90)
        
        # 좌측 선
        path.lineTo(left, bottom - corner_radius)  # 좌측 하단 모서리 위까지
        
        # 좌측 하단 모서리 (둥근 부분)
        path.arcTo(left, bottom - 2*corner_radius, 2*corner_radius, 2*corner_radius, 180, 90)
        
        # 경로 그리기
        self.scene.addPath(path, QPen(QColor("black"), 2))

        # 색상 정의
        color_map = {
            "A_LOAD": QColor(255, 80, 80),     # 적색 - 화물 적재 장소
            "B_LOAD": QColor(255, 80, 80),     # 적색 - 화물 적재 장소
            "CHECKPOINT_A": QColor(80, 180, 255),  # 청색 - 체크포인트
            "CHECKPOINT_B": QColor(80, 180, 255),  # 청색 - 체크포인트
            "CHECKPOINT_C": QColor(80, 180, 255),  # 청색 - 체크포인트
            "CHECKPOINT_D": QColor(80, 180, 255),  # 청색 - 체크포인트
            "GATE_A": QColor(80, 255, 80),     # 녹색 - 게이트
            "GATE_B": QColor(80, 255, 80),     # 녹색 - 게이트
            "BELT": QColor(255, 180, 80),      # 주황색 - 벨트
            "STANDBY": QColor(120, 120, 255)   # 보라색 - 대기 장소
        }

        # 노드 모양 정의
        node_shape = {
            "A_LOAD": "rect", "B_LOAD": "rect", "BELT": "rect",
            "GATE_A": "rect", "GATE_B": "rect",
            "STANDBY": "ellipse",
            "CHECKPOINT_A": "ellipse", "CHECKPOINT_B": "ellipse",
            "CHECKPOINT_C": "ellipse", "CHECKPOINT_D": "ellipse"
        }
        
        # 노드 크기 정의
        node_size = {
            "A_LOAD": (40, 40), "B_LOAD": (40, 40), "BELT": (40, 40),
            "GATE_A": (30, 30), "GATE_B": (30, 30),
            "STANDBY": (40, 40),
            "CHECKPOINT_A": (30, 30), "CHECKPOINT_B": (30, 30),
            "CHECKPOINT_C": (30, 30), "CHECKPOINT_D": (30, 30)
        }

        # 클릭 가능한 시설물 정의
        clickable_facilities = ["A_LOAD", "B_LOAD", "GATE_A", "GATE_B", "BELT"]

        # 노드 그리기
        for key, (x, y) in self.node_coords.items():
            w, h = node_size[key]
            color = color_map.get(key, QColor(200, 200, 200))
            shape_type = node_shape[key]
            
            # 맵 API에서 사용하는 ID로 변환
            facility_id = key
            if key == "A_LOAD":
                facility_id = "LOAD_A"
            elif key == "B_LOAD":
                facility_id = "LOAD_B"
                
            # 라벨 텍스트
            label_text = self.get_label(key)
                
            # 클릭 가능한 시설물인 경우 ClickableFacilityItem 사용
            if key in clickable_facilities:
                # 클릭 가능한 시설물 생성
                facility_item = ClickableFacilityItem(
                    self.scene, shape_type, x, y, w, h, 
                    facility_id, color, label_text, self
                )
                # 시설물 참조 저장
                self.facility_items[key] = facility_item
            else:
                # 일반 시설물 생성
                if shape_type == "ellipse":
                    item = QGraphicsEllipseItem(x - w / 2, y - h / 2, w, h)
                else:
                    item = QGraphicsRectItem(x - w / 2, y - h / 2, w, h)
                item.setBrush(QBrush(color))
                item.setPen(QPen(QColor("black"), 2))
                self.scene.addItem(item)

            # 라벨 위치 조정
            label = QGraphicsTextItem(label_text)
            
            # 노드 위치에 따라 라벨 위치 조정
            if y == top:  # 상단 노드
                label.setPos(x - len(label_text) * 2.5, y - h - 25)
            elif y == bottom:  # 하단 노드
                label.setPos(x - len(label_text) * 2.5, y + 5)
            elif x == left:  # 좌측 노드
                label.setPos(x - len(label_text) * 2, y - 10)
            elif x == right:  # 우측 노드
                label.setPos(x - len(label_text) * 8, y - 10)
            
            self.scene.addItem(label)
            
    def get_label(self, key):
        """노드 레이블 반환"""
        return {
            "A_LOAD": "A 화물 적재 장소",
            "B_LOAD": "B 화물 적재 장소",
            "CHECKPOINT_A": "체크포인트 A",
            "CHECKPOINT_B": "체크포인트 B",
            "CHECKPOINT_C": "체크포인트 C",
            "CHECKPOINT_D": "체크포인트 D",
            "GATE_A": "게이트 A",
            "GATE_B": "게이트 B",
            "BELT": "컨베이어 벨트",
            "STANDBY": "대기 장소 및 충전소"
        }[key]
        
    def show_facility_control_dialog(self, facility_id, facility_name):
        """시설물 제어 다이얼로그 표시"""
        try:
            print(f"[INFO] 시설물 제어 다이얼로그 열기: {facility_id}")
            
            # 다이얼로그 생성
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{facility_name} 제어")
            dialog.setFixedSize(400, 250)
            
            # 레이아웃 설정
            layout = QGridLayout()
            dialog.setLayout(layout)
            
            # 시설물 종류에 따라 다른 제어 UI 표시
            if facility_id in ["LOAD_A", "LOAD_B"]:
                # 적재지 제어
                layout.addWidget(QLabel(f"{facility_name} 상태:"), 0, 0)
                
                status_combo = QComboBox()
                status_combo.addItems(["이용가능", "사용중"])
                layout.addWidget(status_combo, 0, 1)
                
                # 현재 상태 가져오기
                try:
                    facility_data = api_client.get_facility(facility_id)
                    current_status = facility_data.get("status", "AVAILABLE")
                    if current_status == "OCCUPIED":
                        status_combo.setCurrentIndex(1)
                    else:
                        status_combo.setCurrentIndex(0)
                except Exception as e:
                    print(f"[ERROR] 시설물 상태 조회 실패: {e}")
                
                # 저장 버튼
                save_button = QPushButton("상태 변경")
                layout.addWidget(save_button, 1, 0, 1, 2)
                
                # 저장 버튼 클릭 이벤트
                def on_save_click():
                    new_status = "OCCUPIED" if status_combo.currentIndex() == 1 else "AVAILABLE"
                    try:
                        response = api_client.update_facility(facility_id, {"status": new_status})
                        if response.get("success", False):
                            QMessageBox.information(dialog, "상태 변경 성공", 
                                f"{facility_name}의 상태가 성공적으로 변경되었습니다.")
                            dialog.accept()
                        else:
                            error_msg = response.get("message", "알 수 없는 오류")
                            QMessageBox.warning(dialog, "상태 변경 실패", error_msg)
                    except Exception as e:
                        QMessageBox.critical(dialog, "오류", f"상태 변경 중 오류 발생: {e}")
                        
                save_button.clicked.connect(on_save_click)
                
            elif facility_id in ["GATE_A", "GATE_B"]:
                # 게이트 제어
                layout.addWidget(QLabel(f"{facility_name} 상태:"), 0, 0)
                
                status_combo = QComboBox()
                status_combo.addItems(["닫힘", "열림"])
                layout.addWidget(status_combo, 0, 1)
                
                # 현재 상태 가져오기
                try:
                    facility_data = api_client.get_facility(facility_id)
                    current_status = facility_data.get("status", "CLOSED")
                    if current_status == "OPEN":
                        status_combo.setCurrentIndex(1)
                    else:
                        status_combo.setCurrentIndex(0)
                except Exception as e:
                    print(f"[ERROR] 게이트 상태 조회 실패: {e}")
                
                # 닫기 버튼
                close_button = QPushButton("닫기")
                layout.addWidget(close_button, 1, 0)
                
                # 열기 버튼
                open_button = QPushButton("열기")
                layout.addWidget(open_button, 1, 1)
                
                # 버튼 클릭 이벤트
                def on_close_click():
                    try:
                        response = api_client.update_facility(facility_id, {"status": "CLOSED"})
                        if response.get("success", False):
                            QMessageBox.information(dialog, "게이트 닫기 성공", 
                                f"{facility_name}가 성공적으로 닫혔습니다.")
                            dialog.accept()
                        else:
                            error_msg = response.get("message", "알 수 없는 오류")
                            QMessageBox.warning(dialog, "게이트 닫기 실패", error_msg)
                    except Exception as e:
                        QMessageBox.critical(dialog, "오류", f"게이트 닫기 중 오류 발생: {e}")
                        
                def on_open_click():
                    try:
                        response = api_client.update_facility(facility_id, {"status": "OPEN"})
                        if response.get("success", False):
                            QMessageBox.information(dialog, "게이트 열기 성공", 
                                f"{facility_name}가 성공적으로 열렸습니다.")
                            dialog.accept()
                        else:
                            error_msg = response.get("message", "알 수 없는 오류")
                            QMessageBox.warning(dialog, "게이트 열기 실패", error_msg)
                    except Exception as e:
                        QMessageBox.critical(dialog, "오류", f"게이트 열기 중 오류 발생: {e}")
                
                close_button.clicked.connect(on_close_click)
                open_button.clicked.connect(on_open_click)
                
            elif facility_id == "BELT":
                # 벨트 제어
                layout.addWidget(QLabel("벨트 상태:"), 0, 0)
                
                status_combo = QComboBox()
                status_combo.addItems(["정지됨", "작동중"])
                layout.addWidget(status_combo, 0, 1)
                
                # 속도 조절
                layout.addWidget(QLabel("벨트 속도:"), 1, 0)
                
                speed_combo = QComboBox()
                speed_combo.addItems(["25%", "50%", "75%", "100%"])
                layout.addWidget(speed_combo, 1, 1)
                
                # 현재 상태 가져오기
                try:
                    facility_data = api_client.get_facility(facility_id)
                    current_status = facility_data.get("status", "STOPPED")
                    current_speed = facility_data.get("speed", 50)
                    
                    if current_status == "RUNNING":
                        status_combo.setCurrentIndex(1)
                    else:
                        status_combo.setCurrentIndex(0)
                        
                    # 속도에 따른 콤보박스 선택
                    if current_speed <= 25:
                        speed_combo.setCurrentIndex(0)
                    elif current_speed <= 50:
                        speed_combo.setCurrentIndex(1)
                    elif current_speed <= 75:
                        speed_combo.setCurrentIndex(2)
                    else:
                        speed_combo.setCurrentIndex(3)
                except Exception as e:
                    print(f"[ERROR] 벨트 상태 조회 실패: {e}")
                
                # 적용 버튼
                apply_button = QPushButton("적용")
                layout.addWidget(apply_button, 2, 0, 1, 2)
                
                # 적용 버튼 클릭 이벤트
                def on_apply_click():
                    new_status = "RUNNING" if status_combo.currentIndex() == 1 else "STOPPED"
                    new_speed = int(speed_combo.currentText().replace("%", ""))
                    
                    try:
                        response = api_client.update_facility(facility_id, {
                            "status": new_status, 
                            "speed": new_speed
                        })
                        
                        if response.get("success", False):
                            QMessageBox.information(dialog, "벨트 제어 성공", 
                                f"컨베이어 벨트 상태가 성공적으로 변경되었습니다.")
                            dialog.accept()
                        else:
                            error_msg = response.get("message", "알 수 없는 오류")
                            QMessageBox.warning(dialog, "벨트 제어 실패", error_msg)
                    except Exception as e:
                        QMessageBox.critical(dialog, "오류", f"벨트 제어 중 오류 발생: {e}")
                        
                apply_button.clicked.connect(on_apply_click)
            
            # 취소 버튼
            cancel_button = QPushButton("취소")
            cancel_button.clicked.connect(dialog.reject)
            layout.addWidget(cancel_button, 3, 0, 1, 2)
            
            # 다이얼로그 표시
            dialog.exec()
            
            # 시설 상태 업데이트
            self.update_facility_list()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] 시설물 제어 다이얼로그 실패: {e}")
            QMessageBox.critical(self, "오류", f"시설물 제어 다이얼로그 실패: {e}")
        
    def setup_truck(self):
        """트럭 초기화"""
        # TRUCK_01만 생성하여 STANDBY에 위치
        self.truck = TruckIcon("TRUCK_01")
        self.truck.update_position(*self.node_coords["STANDBY"])
        self.scene.addItem(self.truck)
        
    def setup_controls(self):
        """컨트롤 버튼 초기화"""
        # 새 미션 등록 버튼 연결
        new_mission_button = self.findChild(QWidget, "button_new_mission")
        if new_mission_button:
            new_mission_button.clicked.connect(self.open_new_mission_dialog)
        else:
            print("[경고] 'button_new_mission' 버튼을 찾을 수 없습니다")
            
        # 초기화(미션 취소) 버튼 연결
        delete_mission_button = self.findChild(QWidget, "button_delete_mission")
        if delete_mission_button:
            delete_mission_button.clicked.connect(self.cancel_current_mission)
        else:
            print("[경고] 'button_delete_mission' 버튼을 찾을 수 없습니다")
            
        # 수동 제어 모드 버튼 연결
        control_mode_button = self.findChild(QWidget, "button_control_mode")
        if control_mode_button:
            control_mode_button.clicked.connect(self.toggle_control_mode)
        else:
            print("[경고] 'button_control_mode' 버튼을 찾을 수 없습니다")
            
        # 시설 정보 더 보기 버튼 연결
        facility_list_button = self.findChild(QWidget, "button_facility_list")
        if facility_list_button:
            facility_list_button.clicked.connect(self.show_facility_tab)
        else:
            print("[경고] 'button_facility_list' 버튼을 찾을 수 없습니다")
            
        # 미션 목록 더 보기 버튼 연결
        mission_list_button = self.findChild(QWidget, "button_mission_list")
        if mission_list_button:
            mission_list_button.clicked.connect(self.show_mission_tab)
        else:
            print("[경고] 'button_mission_list' 버튼을 찾을 수 없습니다")
            
        # 모든 미션 취소 버튼 연결
        cancel_all_button = self.findChild(QWidget, "pushButton")
        if cancel_all_button:
            cancel_all_button.clicked.connect(self.cancel_all_missions)
        else:
            print("[경고] '모든 미션 취소' 버튼을 찾을 수 없습니다")
            
        # 일시정지 버튼 연결
        pause_button = self.findChild(QWidget, "pushButton_2")
        if pause_button:
            pause_button.clicked.connect(self.pause_truck)
        else:
            print("[경고] '일시정지' 버튼을 찾을 수 없습니다")
            
        # 재시작 버튼 연결
        resume_button = self.findChild(QWidget, "pushButton_3")
        if resume_button:
            resume_button.clicked.connect(self.resume_truck)
        else:
            print("[경고] '재시작' 버튼을 찾을 수 없습니다")

        # 디스펜서 제어 버튼 연결
        dispense_button = self.findChild(QWidget, "button_dispense")
        if dispense_button:
            dispense_button.clicked.connect(self.dispense_cargo)
        else:
            print("[경고] '투하' 버튼을 찾을 수 없습니다")
            
        left_button = self.findChild(QWidget, "button_left")
        if left_button:
            left_button.clicked.connect(self.move_dispenser_left)
        else:
            print("[경고] '디스펜서 왼쪽 이동' 버튼을 찾을 수 없습니다")
            
        right_button = self.findChild(QWidget, "button_right")
        if right_button:
            right_button.clicked.connect(self.move_dispenser_right)
        else:
            print("[경고] '디스펜서 오른쪽 이동' 버튼을 찾을 수 없습니다")
            
    def setup_timer(self):
        """타이머 설정"""
        # 트럭 위치 업데이트 타이머
        self.truck_timer = QTimer(self)
        self.truck_timer.timeout.connect(self.update_truck_position_from_api)
        self.truck_timer.start(200)  # 0.2초마다
        
        # 배터리 상태 업데이트 타이머
        self.battery_timer = QTimer(self)
        self.battery_timer.timeout.connect(self.refresh_battery_status)
        self.battery_timer.start(200)  # 0.2초마다
        
        # 트럭 상태 및 미션 정보 업데이트 타이머
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_truck_status)
        self.status_timer.start(200)  # 0.2초마다
        
        # 컨테이너 상태 업데이트 타이머
        self.container_timer = QTimer(self)
        self.container_timer.timeout.connect(self.update_container_status)
        self.container_timer.start(2000)
        
        # 미션 진행률 업데이트 타이머
        self.mission_progress_timer = QTimer(self)
        self.mission_progress_timer.timeout.connect(self.update_mission_progress)
        self.mission_progress_timer.start(200)  # 0.2초마다
        
        # 시설 상태 목록 업데이트 타이머
        self.facility_list_timer = QTimer(self)
        self.facility_list_timer.timeout.connect(self.update_facility_list)
        self.facility_list_timer.start(5000)  # 5초마다 업데이트
        
        # 미션 목록 업데이트 타이머
        self.mission_list_timer = QTimer(self)
        self.mission_list_timer.timeout.connect(self.update_mission_list)
        self.mission_list_timer.start(5000)  # 5초마다 업데이트
    
    def update_truck_position_from_api(self):
        """트럭 위치 업데이트 (API 호출)"""
        try:
            # api_client를 사용하여 트럭 정보 조회
            data = api_client.get_truck("TRUCK_01")
            
            # location 키를 사용하여 위치 데이터 가져오기
            pos = data.get("position", {}).get("location")
            status = data.get("position", {}).get("status", "IDLE")
            
            # 위치 표시 라벨 업데이트
            position_label = self.findChild(QWidget, "label_truck_position_name")
            if position_label and pos:
                position_label.setText(self.get_location_display_name(pos))
            
            # 위치 정보가 있을 때만 디버그 메시지 출력
            if pos:
                # print(f"[DEBUG] 트럭 위치 데이터: {data.get('position', {})}")
                pass
            
            # 위치 매핑 테이블 - 백엔드에서 보내는 위치를 맵 좌표 키로 변환
            location_mapping = {
                "STANDBY": "STANDBY",
                "CHECKPOINT_A": "CHECKPOINT_A", 
                "GATE_A": "GATE_A",
                "CHECKPOINT_B": "CHECKPOINT_B",
                "LOAD_A": "A_LOAD",     # 백엔드: LOAD_A -> GUI: A_LOAD
                "LOAD_B": "B_LOAD",     # 백엔드: LOAD_B -> GUI: B_LOAD
                "CHECKPOINT_C": "CHECKPOINT_C",
                "GATE_B": "GATE_B",
                "CHECKPOINT_D": "CHECKPOINT_D",
                "BELT": "BELT"
            }
            
            # pos가 None이 아닐 때만 처리
            if pos:
                # 대문자로 통일
                pos_upper = pos.upper()
                # 맵 좌표 키로 변환
                node = location_mapping.get(pos_upper)
                
                if node in self.node_coords:
                    self.truck.update_position(*self.node_coords[node])
                    # STANDBY가 아니거나 상태가 변경되었을 때만 로그 출력
                    if (pos_upper != "STANDBY") or (status != "IDLE"):
                        # print(f"[DEBUG] 트럭 위치 업데이트: {node} (상태: {status})")
                        pass
                else:
                    # print(f"[DEBUG] 매핑되지 않은 위치: {pos_upper} -> {node}")
                    pass
                    
        except Exception as e:
            print(f"[ERROR] 트럭 위치 업데이트 실패: {e}")
        
    def refresh_battery_status(self):
        """배터리 상태 업데이트"""
        # 탭 위젯 참조
        tab_widget = self.findChild(QWidget, "tabWidget")
        if not tab_widget:
            return
        
        # 배터리 상태 위젯 찾기 (새 UI 파일에서는 트럭 탭 안에 progressBar_battery가 있음)
        current_tab = tab_widget.currentWidget()
        if not current_tab:
            return
            
        progress_bar = current_tab.findChild(QWidget, "progressBar_battery")
        if not progress_bar:
            print("[경고] 배터리 프로그레스 바를 찾을 수 없습니다")
            return
        
        try:
            # api_client를 사용하여 모든 트럭 배터리 정보 조회
            data = api_client.get_all_truck_batteries()
            
            # 현재 탭 인덱스에 따라 트럭 ID 결정
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 트럭 데이터 가져오기
            truck_data = data.get(truck_id, {})
            
            # 배터리 상태 업데이트
            self.update_battery_bar(progress_bar, truck_data, truck_id)
            
        except Exception as e:
            print(f"[ERROR] 배터리 상태 업데이트 실패: {e}")
            
    def update_battery_bar(self, progress_bar, truck_data, truck_id):
        """배터리 진행바 업데이트"""
        if not truck_data:  # 데이터가 없는 경우
            # 기본값 설정 - 등록되지 않은 트럭은 회색으로 표시
            progress_bar.setFormat(f"{truck_id}: 미등록")
            progress_bar.setValue(0)
            progress_bar.setStyleSheet("QProgressBar { text-align: center; }")
            return
        
        # 배터리 레벨과 충전 상태 확인
        level = truck_data.get("level", 0)
        is_charging = truck_data.get("is_charging", False)
        
        # 배터리 레벨이 100을 넘지 않도록 제한
        level = min(100, max(0, level))
        
        # 프로그레스 바에 배터리 정보 표시
        progress_bar.setValue(int(level))
        
        # 충전 중일 때 녹색, 아닐 때 배터리 상태에 따라 색상 변경
        if is_charging:
            progress_bar.setFormat(f"{truck_id}: {level:.0f}% (충전 중)")
            progress_bar.setStyleSheet("QProgressBar { text-align: center; }"
                                     "QProgressBar::chunk { background-color: #00aa00; }")
        else:
            progress_bar.setFormat(f"{truck_id}: {level:.0f}%")
            if level < 20:
                progress_bar.setStyleSheet("QProgressBar { text-align: center; }"
                                        "QProgressBar::chunk { background-color: #ff0000; }")
            elif level < 50:
                progress_bar.setStyleSheet("QProgressBar { text-align: center; }"
                                        "QProgressBar::chunk { background-color: #ffaa00; }")
            else:
                progress_bar.setStyleSheet("QProgressBar { text-align: center; }"
                                        "QProgressBar::chunk { background-color: #0000ff; }")
            
    def open_new_mission_dialog(self):
        """새 미션 등록 다이얼로그 표시"""
        try:
            from PyQt6.QtWidgets import QDialog, QComboBox, QGridLayout, QPushButton, QLabel
            
            dialog = QDialog(self)
            dialog.setWindowTitle("새 미션 등록")
            dialog.setFixedSize(400, 250)
            
            layout = QGridLayout()
            
            # 소스 선택
            layout.addWidget(QLabel("출발지:"), 0, 0)
            source_combo = QComboBox()
            source_combo.addItems(["STANDBY", "LOAD_A", "LOAD_B"])
            layout.addWidget(source_combo, 0, 1)
            
            # 목적지 선택
            layout.addWidget(QLabel("목적지:"), 1, 0)
            destination_combo = QComboBox()
            destination_combo.addItems(["STANDBY", "LOAD_A", "LOAD_B", "BELT"])
            layout.addWidget(destination_combo, 1, 1)
            
            # 트럭 선택
            layout.addWidget(QLabel("트럭:"), 2, 0)
            truck_combo = QComboBox()
            truck_combo.addItems(["TRUCK_01", "TRUCK_02", "TRUCK_03"])
            layout.addWidget(truck_combo, 2, 1)
            
            # 화물 유형 선택
            layout.addWidget(QLabel("화물 유형:"), 3, 0)
            cargo_combo = QComboBox()
            cargo_combo.addItems(["A", "B", "C"])
            layout.addWidget(cargo_combo, 3, 1)
            
            # 버튼 배치
            cancel_button = QPushButton("취소")
            cancel_button.clicked.connect(dialog.reject)
            layout.addWidget(cancel_button, 4, 0)
            
            save_button = QPushButton("등록")
            
            def register_mission():
                source = source_combo.currentText()
                destination = destination_combo.currentText()
                truck = truck_combo.currentText()
                cargo_type = cargo_combo.currentText()
                
                try:
                    # API 호출
                    response = api_client.create_mission(
                        truck_id=truck,
                        source=source,
                        destination=destination,
                        cargo_type=cargo_type
                    )
                    
                    if response.get("success", False):
                        mission_id = response.get("mission_id", "알 수 없음")
                        self.show_alert(f"미션이 성공적으로 등록되었습니다. ID: {mission_id}")
                        dialog.accept()
                    else:
                        error_msg = response.get("message", "알 수 없는 오류")
                        self.show_alert(f"미션 등록 실패: {error_msg}")
                        QMessageBox.warning(self, "미션 등록 실패", error_msg)
                except Exception as e:
                    self.show_alert(f"오류: 미션 등록 중 오류 발생 - {e}")
                    QMessageBox.critical(self, "오류", f"미션 등록 중 오류 발생: {e}")
            
            save_button.clicked.connect(register_mission)
            layout.addWidget(save_button, 4, 1)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            self.show_alert(f"오류: 미션 등록 다이얼로그 실패 - {e}")
            print(f"[ERROR] 미션 등록 다이얼로그 실패: {e}")
            
    def cancel_current_mission(self):
        """현재 선택된 트럭의 미션 취소"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                raise ValueError("탭 위젯을 찾을 수 없습니다.")
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 확인 대화상자
            reply = QMessageBox.question(
                self,
                "미션 취소",
                f"{truck_id}의 현재 미션을 취소하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # API 호출
                response = api_client.cancel_current_mission(truck_id)
                
                if response.get("success", False):
                    self.show_alert(f"{truck_id}의 미션이 취소되었습니다.")
                    QMessageBox.information(self, "미션 취소", f"{truck_id}의 미션이 취소되었습니다.")
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    self.show_alert(f"미션 취소 실패: {error_msg}")
                    QMessageBox.warning(self, "미션 취소 실패", error_msg)
        except Exception as e:
            self.show_alert(f"오류: 미션 취소 실패 - {e}")
            print(f"[ERROR] 미션 취소 실패: {e}")
            
    def toggle_control_mode(self):
        """수동 제어 모드 토글"""
        try:
            button = self.findChild(QWidget, "button_control_mode")
            if not button:
                return
                
            # 버튼 상태 확인
            manual_mode_on = button.isChecked()
            
            # API 호출
            response = api_client.set_manual_control_mode(enabled=manual_mode_on)
            
            if response.get("success", False):
                mode_text = "수동 제어 모드 ON" if manual_mode_on else "수동 제어 모드 OFF"
                button.setText(mode_text)
                self.show_alert(f"제어 모드 변경: {mode_text}")
            else:
                error_msg = response.get("message", "알 수 없는 오류")
                self.show_alert(f"제어 모드 변경 실패: {error_msg}")
                
                # 실패 시 버튼 상태 되돌리기
                button.setChecked(not manual_mode_on)
        except Exception as e:
            self.show_alert(f"오류: 제어 모드 변경 실패 - {e}")
            print(f"[ERROR] 제어 모드 변경 실패: {e}")
            
    def show_facility_tab(self):
        """시설 관리 탭으로 이동 (탭 제거됨)"""
        try:
            # 대체 기능: 시설 정보를 알림창에 표시
            self.show_alert("시설 관리 탭이 더 이상 사용되지 않습니다. 시설 상태 정보는 현재 화면에서 확인하세요.")
            
            # 시설 상태 정보 업데이트 강제 호출
            self.update_facility_list()
        except Exception as e:
            self.show_alert(f"오류: {e}")
            print(f"[ERROR] 시설 정보 표시 실패: {e}")
            
    def show_mission_tab(self):
        """미션 관리 탭으로 이동"""
        try:
            main_window = self.window()
            tab_widget = main_window.findChild(QWidget, "main_tab_widget")
            
            if tab_widget:
                # 미션 관리 탭 인덱스 찾기 (일반적으로 1)
                mission_tab_index = 1
                tab_widget.setCurrentIndex(mission_tab_index)
                self.show_alert("미션 관리 탭으로 이동했습니다.")
        except Exception as e:
            self.show_alert(f"오류: 미션 관리 탭 이동 실패 - {e}")
            print(f"[ERROR] 미션 관리 탭 이동 실패: {e}")
    
    def show_alert(self, message):
        """알림 영역에 메시지 표시"""
        text_edit = self.findChild(QWidget, "textEdit_alert")
        if text_edit:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_edit.append(f"[{timestamp}] {message}")
            
            # 항상 마지막 알림이 보이도록 스크롤
            scroll_bar = text_edit.verticalScrollBar()
            if scroll_bar:
                scroll_bar.setValue(scroll_bar.maximum()) 

    def cancel_all_missions(self):
        """모든 미션 취소"""
        try:
            # 확인 대화상자
            reply = QMessageBox.question(
                self,
                "모든 미션 취소",
                "모든 트럭의 미션을 취소하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 현재 미션을 가진 모든 트럭에 대해 미션 취소 요청
                for truck_id in ["TRUCK_01", "TRUCK_02", "TRUCK_03"]:
                    try:
                        response = api_client.cancel_current_mission(truck_id)
                        if response.get("success", False):
                            self.show_alert(f"{truck_id}의 미션이 취소되었습니다.")
                    except Exception as e:
                        self.show_alert(f"{truck_id} 미션 취소 실패: {e}")
                
                self.show_alert("모든 미션 취소 요청이 완료되었습니다.")
        except Exception as e:
            self.show_alert(f"오류: 모든 미션 취소 실패 - {e}")
            print(f"[ERROR] 모든 미션 취소 실패: {e}")
            
    def pause_truck(self):
        """현재 선택된 트럭 작업 일시정지"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                raise ValueError("탭 위젯을 찾을 수 없습니다.")
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 이 부분은 API 구현에 따라 달라질 수 있음
            try:
                # 만약 API에 pause 기능이 있다면 사용
                response = api_client.pause_truck(truck_id)
                if response.get("success", False):
                    self.show_alert(f"{truck_id}가 일시정지되었습니다.")
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    self.show_alert(f"트럭 일시정지 실패: {error_msg}")
            except AttributeError:
                # API에 해당 기능이 없는 경우
                self.show_alert("트럭 일시정지 기능은 현재 구현되지 않았습니다.")
                
        except Exception as e:
            self.show_alert(f"오류: 트럭 일시정지 실패 - {e}")
            print(f"[ERROR] 트럭 일시정지 실패: {e}")
            
    def resume_truck(self):
        """현재 선택된 트럭 작업 재시작"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                raise ValueError("탭 위젯을 찾을 수 없습니다.")
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 이 부분은 API 구현에 따라 달라질 수 있음
            try:
                # 만약 API에 resume 기능이 있다면 사용
                response = api_client.resume_truck(truck_id)
                if response.get("success", False):
                    self.show_alert(f"{truck_id}의 작업이 재시작되었습니다.")
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    self.show_alert(f"트럭 재시작 실패: {error_msg}")
            except AttributeError:
                # API에 해당 기능이 없는 경우
                self.show_alert("트럭 재시작 기능은 현재 구현되지 않았습니다.")
                
        except Exception as e:
            self.show_alert(f"오류: 트럭 재시작 실패 - {e}")
            print(f"[ERROR] 트럭 재시작 실패: {e}")

    def dispense_cargo(self):
        """화물 투하 명령"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                raise ValueError("탭 위젯을 찾을 수 없습니다.")
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 이 부분은 API 구현에 따라 달라질 수 있음
            try:
                # API에 dispense 기능이 있다면 사용
                response = api_client.dispense_cargo(truck_id)
                if response.get("success", False):
                    self.show_alert(f"{truck_id}에서 화물이 투하되었습니다.")
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    self.show_alert(f"화물 투하 실패: {error_msg}")
            except AttributeError:
                # API에 해당 기능이 없는 경우
                self.show_alert("화물 투하 기능은 현재 구현되지 않았습니다.")
                
        except Exception as e:
            self.show_alert(f"오류: 화물 투하 실패 - {e}")
            print(f"[ERROR] 화물 투하 실패: {e}")
            
    def move_dispenser_left(self):
        """디스펜서 왼쪽으로 이동"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                raise ValueError("탭 위젯을 찾을 수 없습니다.")
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 이 부분은 API 구현에 따라 달라질 수 있음
            try:
                # API에 move_dispenser 기능이 있다면 사용
                response = api_client.move_dispenser(truck_id, direction="left")
                if response.get("success", False):
                    self.show_alert(f"{truck_id}의 디스펜서가 왼쪽으로 이동되었습니다.")
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    self.show_alert(f"디스펜서 이동 실패: {error_msg}")
            except AttributeError:
                # API에 해당 기능이 없는 경우
                self.show_alert("디스펜서 이동 기능은 현재 구현되지 않았습니다.")
                
        except Exception as e:
            self.show_alert(f"오류: 디스펜서 이동 실패 - {e}")
            print(f"[ERROR] 디스펜서 이동 실패: {e}")
            
    def move_dispenser_right(self):
        """디스펜서 오른쪽으로 이동"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                raise ValueError("탭 위젯을 찾을 수 없습니다.")
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 이 부분은 API 구현에 따라 달라질 수 있음
            try:
                # API에 move_dispenser 기능이 있다면 사용
                response = api_client.move_dispenser(truck_id, direction="right")
                if response.get("success", False):
                    self.show_alert(f"{truck_id}의 디스펜서가 오른쪽으로 이동되었습니다.")
                else:
                    error_msg = response.get("message", "알 수 없는 오류")
                    self.show_alert(f"디스펜서 이동 실패: {error_msg}")
            except AttributeError:
                # API에 해당 기능이 없는 경우
                self.show_alert("디스펜서 이동 기능은 현재 구현되지 않았습니다.")
                
        except Exception as e:
            self.show_alert(f"오류: 디스펜서 이동 실패 - {e}")
            print(f"[ERROR] 디스펜서 이동 실패: {e}")

    def get_location_display_name(self, location_code):
        """위치 코드를 표시용 이름으로 변환"""
        location_names = {
            "STANDBY": "대기 장소 및 충전소",
            "CHECKPOINT_A": "체크포인트 A",
            "CHECKPOINT_B": "체크포인트 B",
            "CHECKPOINT_C": "체크포인트 C",
            "CHECKPOINT_D": "체크포인트 D",
            "GATE_A": "게이트 A",
            "GATE_B": "게이트 B",
            "LOAD_A": "A 화물 적재 장소",
            "LOAD_B": "B 화물 적재 장소",
            "BELT": "컨베이어 벨트"
        }
        return location_names.get(location_code.upper(), location_code)
        
    def update_truck_status(self):
        """트럭 상태 및 미션 정보 업데이트"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                return
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 트럭 상태 조회
            data = api_client.get_truck(truck_id)
            
            # FSM 상태 업데이트
            fsm_state = data.get("fsm_state", "IDLE")
            fsm_label = self.findChild(QWidget, "label_loc_name_2")
            if fsm_label:
                fsm_label.setText(self.get_fsm_state_display_name(fsm_state))
                
            # 현재 미션 정보 업데이트
            try:
                # 트럭에 할당된 미션 조회
                mission_data = api_client.get_missions(truck_id=truck_id)
                missions = mission_data.get("missions", {})
                
                # 미션 라벨 업데이트
                mission_label = self.findChild(QWidget, "label_mission_target")
                if not mission_label:
                    return
                    
                if missions and len(missions) > 0:
                    # 첫 번째 미션 정보 (가장 최근 할당된 미션)
                    mission = list(missions.values())[0]
                    source = mission.get("source", "")
                    mission_label.setText(f"적재지: {self.get_location_display_name(source)}")
                else:
                    mission_label.setText("할당된 미션 없음")
            except Exception as e:
                print(f"[ERROR] 미션 정보 업데이트 실패: {e}")
                
        except Exception as e:
            print(f"[ERROR] 트럭 상태 업데이트 실패: {e}")
            
    def get_fsm_state_display_name(self, state_code):
        """FSM 상태 코드를 표시용 이름으로 변환"""
        state_names = {
            "IDLE": "대기 중",
            "MOVING": "이동 중",
            "LOADING": "화물 적재 중",
            "UNLOADING": "화물 하역 중",
            "WAITING": "신호 대기 중",
            "CHARGING": "충전 중",
            "ERROR": "오류 상태"
        }
        return state_names.get(state_code.upper(), state_code)
        
    def update_container_status(self):
        """컨테이너 상태 업데이트"""
        try:
            # 하드코딩으로 항상 정상 상태 표시
            # 컨테이너 A 상태 업데이트
            container_a_label = self.findChild(QWidget, "label_con_a_availability")
            if container_a_label:
                container_a_label.setText("이용가능")
            
            # 컨테이너 B 상태 업데이트  
            container_b_label = self.findChild(QWidget, "label_con_b_availabilty")
            if container_b_label:
                container_b_label.setText("이용가능")
                    
        except Exception as e:
            print(f"[ERROR] 컨테이너 상태 업데이트 실패: {e}")
    
    def update_mission_progress(self):
        """미션 진행률 업데이트"""
        try:
            # 현재 선택된 탭 인덱스를 가져와서 트럭 ID 결정
            tab_widget = self.findChild(QWidget, "tabWidget")
            if not tab_widget:
                return
                
            current_index = tab_widget.currentIndex()
            truck_id = f"TRUCK_0{current_index + 1}"  # 0 -> TRUCK_01, 1 -> TRUCK_02, etc.
            
            # 미션 진행률 프로그레스 바 참조
            progress_bar = self.findChild(QWidget, "progressBar_mission")
            if not progress_bar:
                return
                
            try:
                # 트럭 상태 조회
                data = api_client.get_truck(truck_id)
                fsm_state = data.get("fsm_state", "IDLE")
                
                # 트럭에 할당된 미션 조회
                mission_data = api_client.get_missions(truck_id=truck_id)
                missions = mission_data.get("missions", {})
                
                if missions and len(missions) > 0:
                    # 미션이 있는 경우, 진행 상황 계산 (예시: 이동 단계에 따라 진행률 계산)
                    # 실제로는 백엔드에서 진행률 정보를 제공하는 것이 좋겠지만, 여기서는 단순화하여 구현
                    if fsm_state == "IDLE":
                        progress = 0
                    elif fsm_state == "MOVING":
                        progress = 30
                    elif fsm_state == "LOADING":
                        progress = 60
                    elif fsm_state == "UNLOADING":
                        progress = 90
                    else:
                        progress = 50
                        
                    progress_bar.setValue(progress)
                    progress_bar.setFormat(f"미션 진행률: {progress}%")
                else:
                    progress_bar.setValue(0)
                    progress_bar.setFormat("미션 없음")
            except Exception as e:
                print(f"[ERROR] 미션 진행률 업데이트 API 호출 실패: {e}")
                # 오류 시 기본값 표시
                progress_bar.setValue(0)
                progress_bar.setFormat("미션 정보 없음")
                
        except Exception as e:
            print(f"[ERROR] 미션 진행률 업데이트 실패: {e}") 

    def update_facility_list(self):
        """시설 상태 목록 업데이트"""
        facility_text_edit = self.findChild(QWidget, "textEdit_facility_list")
        if not facility_text_edit:
            return
            
        try:
            # 하드코딩으로 항상 정상 상태 표시
            facility_text_edit.clear()
            
            # 게이트 상태 정보
            facility_text_edit.append("<b>게이트 상태:</b>")
            
            # 게이트 A 상태 - 항상 닫힘으로 표시
            facility_text_edit.append("- 게이트 A: 닫힘")
            
            # 게이트 B 상태 - 항상 닫힘으로 표시
            facility_text_edit.append("- 게이트 B: 닫힘")
            
            # 적재 장소 상태 정보
            facility_text_edit.append("")
            facility_text_edit.append("<b>적재 장소 상태:</b>")
            
            # 적재 장소 A 상태 - 항상 이용가능으로 표시
            facility_text_edit.append("- A 화물 적재 장소: 이용가능")
            
            # 적재 장소 B 상태 - 항상 이용가능으로 표시
            facility_text_edit.append("- B 화물 적재 장소: 이용가능")
            
            # 벨트 상태 정보
            facility_text_edit.append("")
            facility_text_edit.append("<b>벨트 상태:</b>")
            
            # 벨트 상태 - 항상 정지됨으로 표시
            facility_text_edit.append("- 컨베이어 벨트: 정지됨")
                
        except Exception as e:
            print(f"[ERROR] 시설 상태 목록 업데이트 실패: {e}")
            facility_text_edit.clear()
            facility_text_edit.append(f"시설 상태 정보 로딩 실패: {e}")
            
    def update_mission_list(self):
        """미션 목록 업데이트"""
        mission_table = self.findChild(QWidget, "tableWidget_mission_list")
        if not mission_table:
            return
            
        try:
            # 미션 정보 가져오기
            try:
                mission_data = api_client.get_missions()
                missions = mission_data.get("missions", {})
                
                # 테이블 초기화
                mission_table.setRowCount(0)
                
                if not missions:
                    return
                
                # 각 미션 정보 표시
                for mission_id, mission in missions.items():
                    status_code = mission.get("status", {}).get("code", "UNKNOWN")
                    source = mission.get("source", "")
                    
                    # 상태 텍스트 변환
                    status_text = ""
                    if status_code == "WAITING":
                        status_text = "대기중"
                    elif status_code == "ASSIGNED":
                        status_text = "할당됨"
                    elif status_code == "COMPLETED":
                        status_text = "완료됨"
                    elif status_code == "CANCELED":
                        status_text = "취소됨"
                    elif status_code == "ERROR":
                        status_text = "오류"
                    else:
                        status_text = status_code
                    
                    # 테이블에 행 추가
                    row = mission_table.rowCount()
                    mission_table.insertRow(row)
                    
                    # 미션 ID 설정
                    id_item = QTableWidgetItem(mission_id)
                    mission_table.setItem(row, 0, id_item)
                    
                    # 적재지 설정
                    source_item = QTableWidgetItem(self.get_location_display_name(source))
                    mission_table.setItem(row, 1, source_item)
                    
                    # 상태 설정
                    status_item = QTableWidgetItem(status_text)
                    mission_table.setItem(row, 2, status_item)
                    
                    # 상태에 따른 행 색상 설정
                    if status_code == "ERROR":
                        for col in range(3):
                            mission_table.item(row, col).setBackground(QColor(255, 100, 100))  # 연한 빨간색
                    elif status_code == "COMPLETED":
                        for col in range(3):
                            mission_table.item(row, col).setBackground(QColor(150, 255, 150))  # 연한 녹색
                    elif status_code == "CANCELED":
                        for col in range(3):
                            mission_table.item(row, col).setForeground(QColor(150, 150, 150))  # 회색
                
                # 컬럼 너비 설정
                self.set_mission_list_column_widths(mission_table)
                
                # 처음 한 번만 리사이즈 이벤트 핸들러 연결
                if not hasattr(mission_table, '_resize_handler_connected'):
                    mission_table.resizeEvent = lambda event: self.resize_mission_list_columns(event, mission_table)
                    mission_table._resize_handler_connected = True
                
            except AttributeError:
                # API 기능이 없는 경우
                mission_table.setRowCount(0)
                
        except Exception as e:
            print(f"[ERROR] 미션 목록 업데이트 실패: {e}")
    
    def set_mission_list_column_widths(self, table):
        """미션 목록 테이블 컬럼 너비를 퍼센트 기준으로 설정"""
        width = table.width()
        
        # 각 컬럼의 너비 비율(%) 설정
        column_widths = {
            0: 33,    # 미션 ID (33%)
            1: 34,    # 적재지 (34%)
            2: 33     # 상태 (33%)
        }
        
        # 컬럼 너비 설정
        for col, percent in column_widths.items():
            if col < table.columnCount():
                pixel_width = int(width * percent / 100)
                table.setColumnWidth(col, pixel_width)
    
    def resize_mission_list_columns(self, event, table):
        """미션 목록 테이블 크기가 변경될 때 컬럼 너비를 재조정"""
        # 컬럼 너비 재설정
        self.set_mission_list_column_widths(table)
        
        # 이벤트 전파
        if hasattr(QWidget, 'resizeEvent'):
            QWidget.resizeEvent(table, event) 