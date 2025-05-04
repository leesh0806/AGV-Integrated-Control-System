from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

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