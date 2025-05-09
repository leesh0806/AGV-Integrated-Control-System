from flask import Flask, jsonify, request, g
import atexit
from backend.truck_status.truck_status_manager import TruckStatusManager
from backend.truck_status.truck_status_db import TruckStatusDB
from backend.mission.mission_manager import MissionManager
from backend.mission.mission_db import MissionDB


# Flask 웹 서버 인스턴스 생성
app = Flask(__name__)

# 전역 상태 관리 인스턴스
status_manager = None
mission_manager = None


# ------------------ 초기화 ----------------------------

# status_manager 초기화
def get_status_manager():
    """TruckStatusManager 초기화"""
    global status_manager
    if status_manager is None:
        print("[DEBUG] TruckStatusManager 초기화")
        status_db = TruckStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        status_manager = TruckStatusManager(status_db)
        print("[DEBUG] TruckStatusManager 초기화 완료")
    return status_manager

# mission_manager 초기화
def get_mission_manager():
    global mission_manager
    if mission_manager is None:
        print("[DEBUG] MissionManager 초기화")
        mission_db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        mission_manager = MissionManager(mission_db)
        print("[DEBUG] MissionManager 초기화 완료")
    return mission_manager


# ------------------ 종료 ----------------------------

def cleanup_managers():
    """애플리케이션 종료 시 리소스 정리"""
    global status_manager, mission_manager
    if status_manager is not None:
        print("[DEBUG] TruckStatusManager 종료")
        status_manager.close()
        status_manager = None

    if mission_manager is not None:
        print("[DEBUG] MissionManager 종료")
        mission_manager.db.close()
        mission_manager = None


atexit.register(cleanup_managers)


# ------------------ 트럭 상태 API ----------------------------

# 전체 트럭 상태 조회
@app.route("/api/trucks", methods=["GET"])
def get_all_trucks():
    manager = get_status_manager()
    trucks = manager.get_all_trucks()
    return jsonify(trucks)

# 특정 트럭 상태 조회
@app.route("/api/trucks/<truck_id>", methods=["GET"])
def get_truck(truck_id):
    manager = get_status_manager()
    truck = manager.get_truck_status(truck_id)
    return jsonify(truck)


@app.route("/api/truck_position", methods=["GET"])
def get_truck_position():
    """전체 트럭 위치 조회"""
    manager = get_status_manager()
    trucks = manager.get_all_trucks()
    response_data = {
        truck_id: truck["position"]
        for truck_id, truck in trucks.items()
    }
    return jsonify(response_data)


@app.route("/api/truck_battery", methods=["GET"])
def get_truck_battery():
    """전체 트럭 배터리 상태 조회"""
    manager = get_status_manager()
    trucks = manager.get_all_trucks()
    response_data = {
        truck_id: truck["battery"]
        for truck_id, truck in trucks.items()
    }
    return jsonify(response_data)


@app.route("/api/truck_battery/<truck_id>", methods=["POST"])
def update_truck_battery(truck_id):
    """특정 트럭 배터리 상태 업데이트"""
    manager = get_status_manager()
    data = request.json
    
    try:
        level = data.get("level", 0)
        is_charging = data.get("is_charging", False)
        
        # 배터리 상태 업데이트
        manager.update_battery(truck_id, level, is_charging)
        
        return jsonify({"status": "success", "message": f"{truck_id} 배터리 업데이트 완료"}), 200
    except Exception as e:
        print(f"[ERROR] 배터리 업데이트 실패: {e}")
        return jsonify({"error": str(e)}), 500


# ------------------ 미션 API ----------------------------

@app.route("/api/missions", methods=["GET"])
def get_all_missions():
    """전체 미션 조회"""
    manager = get_mission_manager()
    missions = manager.get_assigned_and_waiting_missions()
    return jsonify([mission.to_dict() for mission in missions])


@app.route("/api/missions/<mission_id>", methods=["GET"])
def get_mission(mission_id):
    """특정 미션 조회"""
    manager = get_mission_manager()
    mission = manager.find_mission_by_id(mission_id)
    if mission:
        return jsonify(mission.to_dict())
    return jsonify({"error": "Mission not found"}), 404


@app.route("/api/missions", methods=["POST"])
def create_mission():
    """새 미션 생성"""
    data = request.json
    manager = get_mission_manager()
    try:
        mission = manager.create_mission(
            mission_id=data["mission_id"],
            cargo_type=data["cargo_type"],
            cargo_amount=float(data["cargo_amount"]),
            source=data["source"],
            destination=data["destination"]
        )
        if mission:
            return jsonify(mission.to_dict()), 201
        return jsonify({"error": "Mission creation failed"}), 500
    except Exception as err:
        print(f"[ERROR] 미션 생성 실패: {err}")
        return jsonify({"error": str(err)}), 500


@app.route("/api/missions/<mission_id>/complete", methods=["POST"])
def complete_mission(mission_id):
    """미션 완료 처리"""
    manager = get_mission_manager()
    if manager.complete_mission(mission_id):
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Mission completion failed"}), 500


@app.route("/api/missions/<mission_id>/cancel", methods=["POST"])
def cancel_mission(mission_id):
    """미션 취소 처리"""
    manager = get_mission_manager()
    if manager.cancel_mission(mission_id):
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Mission cancellation failed"}), 500


# ------------------ 서버 시작 ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
