from PyQt6.QtWidgets import QWidget, QGraphicsScene, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath
from PyQt6 import uic
import os
from .truck_icon import TruckIcon
from PyQt6.QtCore import Qt

class MainMonitoringTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "main_monitoring_tab.ui")
        uic.loadUi(ui_path, self)  # 새 UI 파일 로드
        self.setup_ui()
        self.setup_map()
        self.setup_truck()

    def setup_ui(self):
        self.scene = QGraphicsScene(self)
        self.graphicsview_map.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 820, 220)

    def setup_map(self):
        # 주요 노드 좌표 (타원형 배치)
        cx, cy, rx, ry = 410, 110, 300, 80
        import math
        def ellipse_pos(angle_deg):
            rad = math.radians(angle_deg)
            return (cx + rx * math.cos(rad), cy + ry * math.sin(rad))
        self.node_coords = {
            "STANDBY": ellipse_pos(270),
            "CHECKPOINT_A": ellipse_pos(315),
            "GATE_A": ellipse_pos(340),
            "CHECKPOINT_B": ellipse_pos(10),
            "B_LOAD": ellipse_pos(45),
            "A_LOAD": ellipse_pos(90),
            "CHECKPOINT_C": ellipse_pos(135),
            "GATE_B": ellipse_pos(160),
            "CHECKPOINT_D": ellipse_pos(200),
            "BELT": ellipse_pos(225)
        }
        # 타원형 경로 그리기
        path = QPainterPath()
        first = True
        for deg in range(270, 270+360, 5):
            x, y = ellipse_pos(deg)
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
        self.scene.addPath(path, QPen(QColor("black"), 2))
        # 색상 정의
        color_map = {
            "A_LOAD": QColor(255, 80, 80),      # 빨강
            "B_LOAD": QColor(255, 80, 80),      # 빨강
            "CHECKPOINT_A": QColor(80, 180, 255),
            "CHECKPOINT_B": QColor(80, 180, 255),
            "CHECKPOINT_C": QColor(80, 180, 255),
            "CHECKPOINT_D": QColor(80, 180, 255),
            "GATE_A": QColor(80, 255, 80),     # 초록
            "GATE_B": QColor(80, 255, 80),     # 초록
            "BELT": QColor(255, 180, 80),      # 주황
            "STANDBY": QColor(120, 120, 255)   # 파랑
        }
        # 노드(원/사각형) 및 라벨 그리기 (색상 적용)
        node_shape = {
            "A_LOAD": "rect", "B_LOAD": "rect", "BELT": "rect",
            "GATE_A": "rect", "GATE_B": "rect",
            "STANDBY": "ellipse",
            "CHECKPOINT_A": "ellipse", "CHECKPOINT_B": "ellipse", "CHECKPOINT_C": "ellipse", "CHECKPOINT_D": "ellipse"
        }
        node_size = {
            "A_LOAD": (30, 30), "B_LOAD": (30, 30), "BELT": (30, 30),
            "GATE_A": (16, 30), "GATE_B": (16, 30),
            "STANDBY": (30, 30),
            "CHECKPOINT_A": (24, 24), "CHECKPOINT_B": (24, 24), "CHECKPOINT_C": (24, 24), "CHECKPOINT_D": (24, 24)
        }
        for key, (x, y) in self.node_coords.items():
            w, h = node_size[key]
            color = color_map.get(key, QColor(200, 200, 200))
            if node_shape[key] == "ellipse":
                item = QGraphicsEllipseItem(x-w/2, y-h/2, w, h)
            else:
                item = QGraphicsRectItem(x-w/2, y-h/2, w, h)
            item.setBrush(QBrush(color))
            item.setPen(QPen(QColor("black"), 2))
            self.scene.addItem(item)
            # 라벨
            label = QGraphicsTextItem(self.get_label(key))
            label.setPos(x + w/2 + 2, y - h/2)
            self.scene.addItem(label)

    def get_label(self, key):
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
        # TRUCK_01만 생성하여 STANDBY에 위치
        self.truck = TruckIcon("TRUCK_01")
        self.truck.update_position(*self.node_coords["STANDBY"])
        self.scene.addItem(self.truck) 