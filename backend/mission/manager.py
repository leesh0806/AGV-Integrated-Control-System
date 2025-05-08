# backend/mission/manager.py

"""
이 MissionManager 클래스는 자율 운송 시스템의 미션 큐 관리 중심 허브입니다. 
미션(할당된 작업)의 현재 상태를 RAM에서 관리하면서, 변경 사항을 MySQL DB와 동기화하는 역할을 합니다.
"""

from collections import deque
from .status import MissionStatus
from .mission import Mission
from backend.mission.db import MissionDB

class MissionManager:
    def __init__(self,db):
        self.db = db
        self.waiting_queue = deque() # 대기 중인 미션들
        self.active_missions = {} # 실행 중인 미션들
        self.completed_missions = {} # 완료된 미션들 
        self.canceled_missions = {} # 취소된 미션들

    def load_from_db(self):
        """데이터베이스에서 미션 로드"""
        print("[DEBUG] DB에서 미션 로드 시작")
        
        # 로드 전 동기화 상태 확인
        is_synced, only_in_db, only_in_queue = self.db.verify_waiting_missions(self.waiting_queue)
        if not is_synced:
            print("[WARNING] 로드 전 waiting_queue와 DB가 동기화되지 않았습니다.")
            if only_in_queue:
                print(f"[WARNING] waiting_queue에만 있는 미션을 DB에 저장합니다.")
                for mission in self.waiting_queue:
                    if mission.mission_id in only_in_queue:
                        self.db.save_mission(mission)
        
        missions = self.db.load_all_active_and_waiting_missions()
        print(f"[DEBUG] DB에서 가져온 미션 수: {len(missions)}")
        self.waiting_queue.clear()
        self.active_missions.clear()
        
        for mission_data in missions:
            print(f"[DEBUG] 미션 데이터: {mission_data}")
            try:
                # 튜플 데이터를 Mission 객체로 변환
                mission = Mission(
                    mission_id=mission_data[0],
                    cargo_type=mission_data[1],
                    cargo_amount=mission_data[2],
                    source=mission_data[3],
                    destination=mission_data[4]
                )
                mission.status = MissionStatus[mission_data[5]]  # 문자열을 enum으로 변환
                mission.assigned_truck_id = mission_data[6]
                mission.timestamp_created = mission_data[8]
                mission.timestamp_assigned = mission_data[9]
                mission.timestamp_completed = mission_data[10]
                
                print(f"[DEBUG] 변환된 미션: {mission.mission_id}, 상태: {mission.status.name}, 트럭ID: {mission.assigned_truck_id}")
                
                if mission.status == MissionStatus.WAITING:
                    self.waiting_queue.append(mission)
                    print(f"[DEBUG] 대기 큐에 추가: {mission.mission_id}")
                elif mission.status == MissionStatus.ASSIGNED:
                    self.active_missions[mission.assigned_truck_id] = mission
                    print(f"[DEBUG] 활성 미션에 추가: {mission.mission_id} (트럭: {mission.assigned_truck_id})")
                else:
                    print(f"[DEBUG] 미션 상태 무시: {mission.mission_id} (상태: {mission.status.name})")
            except Exception as e:
                print(f"[ERROR] 미션 데이터 변환 중 오류 발생: {e}")
                continue
        
        print(f"[DEBUG] 최종 대기 큐 크기: {len(self.waiting_queue)}")
        print(f"[DEBUG] 최종 활성 미션 수: {len(self.active_missions)}")
        
        # 로드 후 동기화 상태 확인
        is_synced, only_in_db, only_in_queue = self.db.verify_waiting_missions(self.waiting_queue)
        if not is_synced:
            print("[ERROR] 로드 후에도 waiting_queue와 DB가 동기화되지 않았습니다.")
        
        # 대기 중인 미션이 있으면 트럭들에게 알림
        if len(self.waiting_queue) > 0 and hasattr(self, 'command_sender') and self.command_sender:
            print(f"[📢 미션 알림] 대기 중인 미션 {len(self.waiting_queue)}개가 있습니다.")
            self.command_sender.broadcast("MISSIONS_AVAILABLE", {
                "count": len(self.waiting_queue)
            })

    def get_all_active_and_waiting_missions(self):
        """현재 로드된 모든 활성 및 대기 중인 미션 반환"""
        all_missions = list(self.waiting_queue) + list(self.active_missions.values())
        return all_missions

    # 미션 추가
    def add_mission(self, mission):
        self.waiting_queue.append(mission)
        self.db.save_mission(mission)

    # 미션 완료
    def complete_mission(self, mission_id):
        if mission_id in self.active_missions:
            mission = self.active_missions.pop(mission_id)
            mission.update_status(MissionStatus.COMPLETED)
            self.completed_missions[mission_id] = mission
            self.db.save_mission(mission)

    # 미션 취소
    def cancel_mission(self, mission_id):
        if mission_id in self.active_missions:
            mission = self.active_missions.pop(mission_id)
            mission.cancel()
            self.canceled_missions[mission_id] = mission
            self.db.save_mission(mission)
            return
        
        for mission in list(self.waiting_queue):
            if mission.mission_id == mission_id:
                self.waiting_queue.remove(mission)
                mission.cancel()
                self.canceled_missions[mission_id] = mission
                self.db.save_mission(mission)
                return
            
    # 트럭에 미션 할당
    def assign_next_to_truck(self, truck_id):
        """트럭에 다음 미션 할당"""
        print(f"[DEBUG] {truck_id}의 미션 할당 요청")
        
        # waiting_queue가 비어있으면 DB에서 새로 로드
        if not self.waiting_queue:
            print("[DEBUG] waiting_queue가 비어있어 DB에서 새로 로드합니다.")
            self.load_from_db()
        
        print(f"[DEBUG] 현재 waiting_queue 크기: {len(self.waiting_queue)}")
        
        if self.waiting_queue:
            # waiting_queue에서 첫 번째 미션 가져오기
            mission = self.waiting_queue.popleft()
            print(f"[DEBUG] 할당할 미션: {mission.mission_id}")
            
            try:
                # 트럭에 할당
                mission.assign_to_truck(truck_id)
                self.active_missions[truck_id] = mission
                self.db.save_mission(mission)
                print(f"[DEBUG] {truck_id}에 미션 {mission.mission_id} 할당 완료")
                return mission
            except Exception as e:
                print(f"[ERROR] 미션 할당 중 오류 발생: {e}")
                # 실패한 경우 미션을 다시 waiting_queue에 추가
                self.waiting_queue.appendleft(mission)
                return None
        else:
            print(f"[DEBUG] {truck_id}에 할당할 대기 중인 미션이 없습니다.")
            
        return None
    
    # 트럭에 할당된 미션 조회
    def get_mission_by_truck(self, truck_id):
        for mission in self.active_missions.values():
            if mission.assigned_truck_id == truck_id:
                return mission
        return None

    # 미션 저장
    def save_to_db(self):
        for mission in self.missions:
            if mission.status_code == "COMPLETED" and mission.timestamp_completed:
                self.db.update_mission_completion(
                    mission_id = mission.mission_id,
                    status_code="COMPLETED",
                    status_label="완료됨",
                    timestamp_completed=mission.timestamp_completed
                )

    def reload_from_db(self):
        """데이터베이스에서 미션을 다시 로드"""
        print("[DEBUG] DB에서 미션 다시 로드 시작")
        self.load_from_db()
        print("[DEBUG] DB에서 미션 다시 로드 완료")