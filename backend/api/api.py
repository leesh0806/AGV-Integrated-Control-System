from flask import Flask, jsonify, request, g
import threading
from backend.truck_status.truck_state_manager import TruckStatusManager
from backend.truck_status.db import TruckStatusDB
import atexit

# Flask 웹 서버 인스턴스 생성
# 이후 /api/... 경로의 REST API를 구성하는 데 사용
app = Flask(__name__)

# 전역 TruckStatusManager 인스턴스
status_manager = None

# -------------------------------------------------------------------

# TruckStatusManager 인스턴스 초기화
def get_status_manager():
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
        # 초기 상태 설정
        for truck_id in ["TRUCK_01", "TRUCK_02", "TRUCK_03"]:
            status_manager.update_battery(truck_id, 100, False)
            status_manager.update_position(truck_id, "STANDBY", "IDLE")
        print("[DEBUG] 초기 상태 설정 완료")
    return status_manager

# TruckStatusManager 인스턴스 종료
def cleanup_status_manager():
    global status_manager
    if status_manager is not None:
        print("[DEBUG] TruckStatusManager 종료")
        status_manager.close()
        status_manager = None

# 종료 시 정리
atexit.register(cleanup_status_manager)

# -------------------------------- GET --------------------------------

# 전체 트럭 상태 조회 API
@app.route("/api/trucks", methods=["GET"])
def get_all_trucks():
    status_manager = get_status_manager()
    trucks = status_manager.get_all_trucks()
    return jsonify(trucks)

# 특정 트럭 상태 조회 API
@app.route("/api/trucks/<truck_id>", methods=["GET"])
def get_truck(truck_id):
    status_manager = get_status_manager()
    truck = status_manager.get_truck_status(truck_id)
    return jsonify(truck)

# 전체 트럭 위치 조회 API
@app.route("/api/truck_position", methods=["GET"])
def get_truck_position():
    status_manager = get_status_manager()
    trucks = status_manager.get_all_trucks()
    response_data = {
        truck_id: truck["position"]
        for truck_id, truck in trucks.items()
    }
    return jsonify(response_data)

# 전체 트럭 배터리 상태 조회 API    
@app.route("/api/truck_battery", methods=["GET"])
def get_truck_battery():
    status_manager = get_status_manager()
    trucks = status_manager.get_all_trucks()
    response_data = {
        truck_id: truck["battery"]
        for truck_id, truck in trucks.items()
    }
    return jsonify(response_data)

# ---------------------------- POST ----------------------------

# 트럭 상태 업데이트 API
@app.route("/api/trucks/<truck_id>", methods=["POST"])
def update_truck(truck_id):
    data = request.json
    print(f"[DEBUG] 트럭 상태 업데이트 요청: {truck_id} - {data}")
    
    status_manager = get_status_manager()
    truck = status_manager.get_truck_status(truck_id)
    
    # 배터리 업데이트
    if "battery" in data:
        battery_data = data["battery"]
        level = battery_data.get("level")
        is_charging = battery_data.get("is_charging")
        
        if level is not None:
            # 배터리가 100%일 때는 충전 상태를 False로 설정
            if level == 100 and is_charging == True:
                print(f"[DEBUG] 배터리가 100%이므로 충전 상태를 False로 자동 설정")
                is_charging = False
            
            print(f"[DEBUG] 배터리 상태 업데이트 전: {truck_id} - {truck['battery']}")
            status_manager.update_battery(truck_id, level, is_charging)
            print(f"[DEBUG] 배터리 상태 업데이트 후: {truck_id} - {status_manager.get_truck_status(truck_id)['battery']}")
    
    # 위치 업데이트
    if "position" in data:
        position_data = data["position"]
        position = position_data.get("current")
        state = position_data.get("state")
        
        if position is not None and state is not None:
            print(f"[DEBUG] 위치 상태 업데이트 전: {truck_id} - {truck['position']}")
            status_manager.update_position(truck_id, position, state)
            print(f"[DEBUG] 위치 상태 업데이트 후: {truck_id} - {status_manager.get_truck_status(truck_id)['position']}")
    
    return jsonify({"status": "success"})


# 특정 트럭 배터리 상태 업데이트 API
@app.route("/api/truck_battery/<truck_id>", methods=["POST"])
def update_truck_battery(truck_id):
    data = request.json
    print(f"[DEBUG] 배터리 업데이트 요청: {truck_id} - {data}")
    level = data.get("level")
    is_charging = data.get("is_charging")
    
    # 배터리가 100%일 때는 충전 상태를 False로 설정 (시뮬레이션 초기 상태용)
    if level == 100 and is_charging == True:
        print(f"[DEBUG] 배터리가 100%이므로 충전 상태를 False로 자동 설정")
        is_charging = False
    
    if level is not None:
        status_manager = get_status_manager()
        print(f"[DEBUG] 배터리 상태 업데이트 전: {truck_id} - {status_manager.get_truck_status(truck_id)['battery']}")
        status_manager.update_battery(truck_id, level, is_charging)
        print(f"[DEBUG] 배터리 상태 업데이트 후: {truck_id} - {status_manager.get_truck_status(truck_id)['battery']}")
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid data"}), 400


# 특정 트럭 위치 업데이트 API
@app.route("/api/truck_position/<truck_id>", methods=["POST"])
def update_truck_position(truck_id):
    data = request.json
    print(f"[DEBUG] 위치 업데이트 요청: {truck_id} - {data}")
    position = data.get("position")
    state = data.get("state")
    
    if position is not None and state is not None:
        status_manager = get_status_manager()
        print(f"[DEBUG] 위치 상태 업데이트 전: {truck_id} - {status_manager.get_truck_status(truck_id)['position']}")
        status_manager.update_position(truck_id, position, state)
        print(f"[DEBUG] 위치 상태 업데이트 후: {truck_id} - {status_manager.get_truck_status(truck_id)['position']}")
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid data"}), 400

# -------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True) 