from flask import Flask, jsonify, request, g
import threading
from backend.battery.manager import BatteryManager
from backend.battery.db import BatteryDB
import atexit

# Flask 웹 서버 인스턴스 생성
# 이후 /api/... 경로의 REST API를 구성하는 데 사용
app = Flask(__name__)

# 전역 변수로 트럭 위치를 저장
# 실제 시스템에서는 공유 메모리/DB 등으로 대체
TRUCK_STATUS = {
    "TRUCK_01": "STANDBY"
}

# 전역 BatteryManager 인스턴스
battery_manager = None

def get_battery_manager():
    global battery_manager
    if battery_manager is None:
        print("[DEBUG] BatteryManager 초기화")
        battery_db = BatteryDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        battery_manager = BatteryManager(battery_db)
        # 초기 배터리 상태 설정
        battery_manager.update_battery("TRUCK_01", 100, False)
        battery_manager.update_battery("TRUCK_02", 100, False)
        battery_manager.update_battery("TRUCK_03", 100, False)
        print("[DEBUG] 초기 배터리 상태 설정 완료")
    return battery_manager

def cleanup_battery_manager():
    global battery_manager
    if battery_manager is not None:
        print("[DEBUG] BatteryManager 종료")
        battery_manager.close()
        battery_manager = None

# 애플리케이션 종료 시 정리
atexit.register(cleanup_battery_manager)

# 트럭 상태 조회 API
@app.route("/api/truck_status", methods=["GET"])
def get_truck_status():
    return jsonify({
        "truck_id": "TRUCK_01",
        "position": TRUCK_STATUS["TRUCK_01"]
    })

# 트럭 배터리 상태 조회 API
@app.route("/api/truck_battery", methods=["GET"])
def get_truck_battery():
    battery_manager = get_battery_manager()
    batteries = battery_manager.get_all_batteries()
    response_data = {
        truck_id: battery.to_dict()
        for truck_id, battery in batteries.items()
    }
    print(f"[DEBUG] 배터리 상태 응답: {response_data}")
    return jsonify(response_data)

# 배터리 상태 업데이트 API
@app.route("/api/truck_battery/<truck_id>", methods=["POST"])
def update_truck_battery(truck_id):
    data = request.json
    print(f"[DEBUG] 배터리 업데이트 요청: {truck_id} - {data}")
    level = data.get("level")
    is_charging = data.get("is_charging")
    
    if level is not None:
        battery_manager = get_battery_manager()
        print(f"[DEBUG] 배터리 상태 업데이트 전: {truck_id} - {battery_manager.get_battery(truck_id).to_dict()}")
        battery_manager.update_battery(truck_id, level, is_charging)
        print(f"[DEBUG] 배터리 상태 업데이트 후: {truck_id} - {battery_manager.get_battery(truck_id).to_dict()}")
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid data"}), 400

# 트럭 위치 설정 API
def set_truck_position(truck_id, position):
    TRUCK_STATUS[truck_id] = position

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True) 