from backend.mission.manager import MissionManager
from backend.mission.db import MissionDB
from backend.mission.mission import Mission

# DB 접속 정보는 환경에 맞게 수정하세요
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "jinhyuk2dacibul"
DB_NAME = "dust"

db = MissionDB(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
manager = MissionManager(db)

# 미션 생성 (필요에 따라 값 수정)
mission = Mission(
    mission_id="TEST001",
    cargo_type="SAND",
    cargo_amount=10,
    source="LOAD_A",
    destination="BELT"
)
manager.add_mission(mission)
print("미션 추가 완료") 