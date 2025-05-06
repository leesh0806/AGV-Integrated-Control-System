from flask import Flask, jsonify
import threading

# Flask 웹 서버 인스턴스 생성
# 이후 /api/... 경로의 REST API를 구성하는 데 사용
app = Flask(__name__)

# 전역 변수로 트럭 위치를 저장
# 실제 시스템에서는 공유 메모리/DB 등으로 대체
TRUCK_STATUS = {
    "TRUCK_01": "STANDBY"
}

# 전역 변수로 트럭 배터리 상태를 저장
TRUCK_BATTERY = {
    "TRUCK_01": 100,
    "TRUCK_02": 100,
    "TRUCK_03": 100,
}

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
    return jsonify(TRUCK_BATTERY)

# 트럭 위치 설정 API
def set_truck_position(truck_id, position):
    TRUCK_STATUS[truck_id] = position

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True) 