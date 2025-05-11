from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem
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
            
        # 초기화
        self.setup_map()
        self.setup_truck()
        self.setup_timer()
        
    def sizeHint(self):
        # 권장 크기 힌트 제공 (Qt 레이아웃 시스템에서 사용)
        return QSize(1200, 600)
        
    def setup_map(self):
        """맵 초기화 (이전 MainMonitoringTab의 기능)"""
        # 씬 생성
        self.scene = QGraphicsScene(self)
        self.graphicsView_map.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 820, 220)
        
        # 중심 좌표와 반지름 (더 넓게)
        cx, cy, r = 375, 130, 220

        def ellipse_pos(angle_deg):
            rad = math.radians(angle_deg)
            return (cx + r * math.cos(rad), cy + r * math.sin(rad))

        # 노드 위치 정의 (원형 배치)
        self.node_coords = {
            "STANDBY": ellipse_pos(270),
            "CHECKPOINT_A": ellipse_pos(315),
            "GATE_A": ellipse_pos(345),
            "CHECKPOINT_B": ellipse_pos(15),
            "B_LOAD": ellipse_pos(45),
            "A_LOAD": ellipse_pos(90),
            "CHECKPOINT_C": ellipse_pos(135),
            "GATE_B": ellipse_pos(165),
            "CHECKPOINT_D": ellipse_pos(200),
            "BELT": ellipse_pos(225)
        }

        # 원형 경로 그리기
        path = QPainterPath()
        first = True
        for deg in range(0, 361, 5):
            x, y = ellipse_pos(deg)
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
        self.scene.addPath(path, QPen(QColor("black"), 2))

        # 색상 정의
        color_map = {
            "A_LOAD": QColor(255, 80, 80),
            "B_LOAD": QColor(255, 80, 80),
            "CHECKPOINT_A": QColor(80, 180, 255),
            "CHECKPOINT_B": QColor(80, 180, 255),
            "CHECKPOINT_C": QColor(80, 180, 255),
            "CHECKPOINT_D": QColor(80, 180, 255),
            "GATE_A": QColor(80, 255, 80),
            "GATE_B": QColor(80, 255, 80),
            "BELT": QColor(255, 180, 80),
            "STANDBY": QColor(120, 120, 255)
        }

        node_shape = {
            "A_LOAD": "rect", "B_LOAD": "rect", "BELT": "rect",
            "GATE_A": "rect", "GATE_B": "rect",
            "STANDBY": "ellipse",
            "CHECKPOINT_A": "ellipse", "CHECKPOINT_B": "ellipse",
            "CHECKPOINT_C": "ellipse", "CHECKPOINT_D": "ellipse"
        }
        node_size = {
            "A_LOAD": (30, 30), "B_LOAD": (30, 30), "BELT": (30, 30),
            "GATE_A": (16, 30), "GATE_B": (16, 30),
            "STANDBY": (30, 30),
            "CHECKPOINT_A": (24, 24), "CHECKPOINT_B": (24, 24),
            "CHECKPOINT_C": (24, 24), "CHECKPOINT_D": (24, 24)
        }

        for key, (x, y) in self.node_coords.items():
            w, h = node_size[key]
            color = color_map.get(key, QColor(200, 200, 200))
            if node_shape[key] == "ellipse":
                item = QGraphicsEllipseItem(x - w / 2, y - h / 2, w, h)
            else:
                item = QGraphicsRectItem(x - w / 2, y - h / 2, w, h)
            item.setBrush(QBrush(color))
            item.setPen(QPen(QColor("black"), 2))
            self.scene.addItem(item)

            # 라벨 위치 약간 위쪽으로 보정
            label = QGraphicsTextItem(self.get_label(key))
            label.setPos(x + w / 2 + 4, y - h / 2 - 10)
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
        
    def setup_truck(self):
        """트럭 초기화"""
        # TRUCK_01만 생성하여 STANDBY에 위치
        self.truck = TruckIcon("TRUCK_01")
        self.truck.update_position(*self.node_coords["STANDBY"])
        self.scene.addItem(self.truck)
        
    def setup_timer(self):
        """타이머 설정"""
        # 트럭 위치 업데이트 타이머
        self.truck_timer = QTimer(self)
        self.truck_timer.timeout.connect(self.update_truck_position_from_api)
        self.truck_timer.start(1000)  # 1초마다
        
        # 배터리 상태 업데이트 타이머
        self.battery_timer = QTimer(self)
        self.battery_timer.timeout.connect(self.refresh_battery_status)
        self.battery_timer.start(1000)
    
    def update_truck_position_from_api(self):
        """트럭 위치 업데이트 (API 호출)"""
        try:
            # api_client를 사용하여 트럭 정보 조회
            data = api_client.get_truck("TRUCK_01")
            
            # location 키를 사용하여 위치 데이터 가져오기
            pos = data.get("position", {}).get("location")
            status = data.get("position", {}).get("status", "IDLE")
            
            # 위치 정보가 있을 때만 디버그 메시지 출력
            if pos:
                # print(f"[DEBUG] 트럭 위치 데이터: {data.get('position', {})}")
                pass
            
            # 위치 매핑 테이블 - 백엔드에서 보내는 위치를 맵 좌표 키로 변환
            location_mapping = {
                "STANDBY": "STANDBY",
                "CHECKPOINT_A": "CHECKPOINT_A", 
                "CHECKPOINT_B": "CHECKPOINT_B",
                "CHECKPOINT_C": "CHECKPOINT_C",
                "CHECKPOINT_D": "CHECKPOINT_D",
                "GATE_A": "GATE_A",
                "GATE_B": "GATE_B",
                "LOAD_A": "A_LOAD",     # 백엔드: LOAD_A -> GUI: A_LOAD
                "LOAD_B": "B_LOAD",     # 백엔드: LOAD_B -> GUI: B_LOAD
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
        # 배터리 상태 위젯 참조 - 수정된 UI 파일의 객체 이름 사용
        widgets = [
            self.progressBar_battery_truck1,
            self.progressBar_battery_truck2,
            self.progressBar_battery_truck3
        ]
        
        # 참조가 없는 경우 종료
        if not all(widgets):
            return
            
        progressBar_battery_truck1, progressBar_battery_truck2, progressBar_battery_truck3 = widgets
        
        try:
            # api_client를 사용하여 모든 트럭 배터리 정보 조회
            data = api_client.get_all_truck_batteries()
            
            # 주기적으로 반복되는 로그는 TRUCK_01에 실제 데이터가 있을 때만 출력
            if "TRUCK_01" in data and data["TRUCK_01"]:
                # print(f"[DEBUG] 배터리 데이터 수신: {data}")
                pass
            
            def update_battery_bar(progress_bar, truck_data, truck_id):
                if not truck_data:  # 데이터가 없는 경우
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
                    progress_bar.setValue(0)
                    # 트럭 미등록 표시 추가
                    progress_bar.setFormat(f"{truck_id} (미등록)")
                    return
                    
                # 배터리 레벨 (기본값 0)
                level = float(truck_data.get("level", 0))
                # 충전 중 여부 (기본값 False)
                is_charging = truck_data.get("is_charging", False)
                
                # 배터리 상태가 변경되었을 때만 로그 출력
                if hasattr(progress_bar, "last_level") and hasattr(progress_bar, "last_charging"):
                    if progress_bar.last_level != level or progress_bar.last_charging != is_charging:
                        # print(f"[DEBUG] 배터리 레벨: {level}%, 충전중: {is_charging}")
                        pass
                else:
                    # print(f"[DEBUG] 배터리 레벨: {level}%, 충전중: {is_charging}")
                    pass
                
                # 현재 상태 저장
                progress_bar.last_level = level
                progress_bar.last_charging = is_charging
                
                # 배터리 상태에 따른 색상 설정
                if is_charging:
                    color = "#0000FF"  # 충전 중: 파란색
                elif level <= 30:
                    color = "#FF0000"  # 배터리 위험: 빨간색
                elif level <= 50:
                    color = "#FFA500"  # 배터리 경고: 주황색
                else:
                    color = "#00FF00"  # 배터리 충분: 초록색
                    
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
                
                # 프로그레스바 업데이트
                progress_bar.setStyleSheet(style)
                progress_bar.setValue(int(level))
                # 기본 형식으로 복원
                progress_bar.setFormat("%p%")
                
            # 각 트럭 배터리 상태 업데이트
            update_battery_bar(progressBar_battery_truck1, data.get("TRUCK_01", {}), "TRUCK_01")
            update_battery_bar(progressBar_battery_truck2, data.get("TRUCK_02", {}), "TRUCK_02")
            update_battery_bar(progressBar_battery_truck3, data.get("TRUCK_03", {}), "TRUCK_03")
                
        except Exception as e:
            print(f"[ERROR] 배터리 상태 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()  # 상세한 오류 정보 출력
            # 에러 발생 시 모든 배터리 표시 비활성화
            for widget in widgets:
                widget.setValue(0)
                widget.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid grey;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #f0f0f0;
                    }
                    QProgressBar::chunk {
                        background-color: #999999;
                        width: 10px;
                        margin: 0.5px;
                    }
                """) 