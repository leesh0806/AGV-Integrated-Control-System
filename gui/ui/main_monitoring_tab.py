from PyQt6.QtWidgets import QWidget, QGraphicsScene, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath
from PyQt6.QtCore import Qt, QTimer
from PyQt6 import uic
import os
from .truck_icon import TruckIcon
import requests

class MainMonitoringTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "main_monitoring_tab.ui")
        uic.loadUi(ui_path, self)  # 새 UI 파일 로드
        self.setup_ui()
        self.setup_map()
        self.setup_truck()
        self.setup_timer()

    def setup_ui(self):
        self.scene = QGraphicsScene(self)
        self.graphicsview_map.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 820, 220)

    def setup_map(self):
        # 중심 좌표와 반지름 (더 넓게)
        cx, cy, r = 375, 130, 220

        import math
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

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_truck_position_from_api)
        self.timer.start(1000)  # 1초마다

    def update_truck_position_from_api(self):
        try:
            resp = requests.get("http://localhost:5001/api/truck_status", timeout=0.5)
            if resp.status_code == 200:
                data = resp.json()
                pos = data.get("position")
                # pos가 load_a, load_b 등 소문자로 올 수 있으니 대문자로 변환
                pos_key = pos.upper() if pos else None
                # node_coords의 키와 매칭
                if pos_key == "LOAD_A":
                    node = "A_LOAD"
                elif pos_key == "LOAD_B":
                    node = "B_LOAD"
                else:
                    node = pos_key
                if node in self.node_coords:
                    self.truck.update_position(*self.node_coords[node])
        except Exception as e:
            pass  # 네트워크 오류 등 무시 