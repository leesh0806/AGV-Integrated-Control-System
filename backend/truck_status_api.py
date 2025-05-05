from flask import Flask, jsonify
import threading

app = Flask(__name__)

# 전역 변수로 트럭 위치를 저장 (실제 시스템에서는 공유 메모리/DB 등으로 대체)
TRUCK_STATUS = {
    "TRUCK_01": "STANDBY"
}

TRUCK_BATTERY = {
    "TRUCK_01": 100,
    "TRUCK_02": 100,
    "TRUCK_03": 100,
}

@app.route("/api/truck_status", methods=["GET"])
def get_truck_status():
    # 단일 트럭만 반환
    return jsonify({
        "truck_id": "TRUCK_01",
        "position": TRUCK_STATUS["TRUCK_01"]
    })

@app.route("/api/truck_battery", methods=["GET"])
def get_truck_battery():
    return jsonify(TRUCK_BATTERY)

# 예시: 외부에서 위치를 바꿀 수 있는 함수 (실제 연동 시 백엔드에서 갱신)
def set_truck_position(truck_id, position):
    TRUCK_STATUS[truck_id] = position

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True) 