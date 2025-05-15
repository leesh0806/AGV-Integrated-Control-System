from flask import Blueprint, jsonify, request
from backend.rest_api.managers import get_mission_manager

# 미션 관련 API 블루프린트 생성
mission_api = Blueprint('mission_api', __name__)

# ------------------ 미션 API ----------------------------

@mission_api.route("/missions", methods=["GET"])
def get_all_missions():
    """전체 미션 조회"""
    manager = get_mission_manager()
    missions = manager.get_assigned_and_waiting_missions()
    return jsonify({
        "success": True,
        "missions": missions
    })


@mission_api.route("/missions/<mission_id>", methods=["GET"])
def get_mission(mission_id):
    """특정 미션 조회"""
    manager = get_mission_manager()
    mission = manager.find_mission_by_id(mission_id)
    if mission:
        return jsonify(mission.to_dict())
    return jsonify({"error": "Mission not found"}), 404


@mission_api.route("/missions", methods=["POST"])
def create_mission():
    """새 미션 생성"""
    data = request.json
    manager = get_mission_manager()
    try:
        # 필수 파라미터 검증
        required_fields = ["source", "destination", "cargo_type"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False, 
                "message": f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
            }), 400
            
        # 미션 ID 생성 (없는 경우)
        mission_id = data.get("mission_id")
        if not mission_id:
            import uuid
            mission_id = f"MISSION_{uuid.uuid4().hex[:8].upper()}"
        
        # 화물 양 기본값 (없는 경우)
        cargo_amount = data.get("cargo_amount", 1.0)
        
        # 미션 생성
        mission = manager.create_mission(
            mission_id=mission_id,
            cargo_type=data["cargo_type"],
            cargo_amount=float(cargo_amount),
            source=data["source"],
            destination=data["destination"]
        )
        
        # 트럭 할당 (truck_id가 있는 경우)
        if "truck_id" in data and data["truck_id"]:
            manager.assign_mission_to_truck(mission.mission_id, data["truck_id"])
        
        if mission:
            return jsonify({
                "success": True,
                "mission_id": mission.mission_id,
                "message": "미션이 성공적으로 생성되었습니다."
            }), 201
            
        return jsonify({
            "success": False,
            "message": "미션 생성 실패"
        }), 500
        
    except Exception as err:
        print(f"[ERROR] 미션 생성 실패: {err}")
        return jsonify({
            "success": False,
            "message": str(err)
        }), 500


@mission_api.route("/missions/<mission_id>/complete", methods=["POST"])
def complete_mission(mission_id):
    """미션 완료 처리"""
    manager = get_mission_manager()
    if manager.complete_mission(mission_id):
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Mission completion failed"}), 500


@mission_api.route("/missions/<mission_id>/cancel", methods=["POST"])
def cancel_mission(mission_id):
    """미션 취소 처리"""
    manager = get_mission_manager()
    if manager.cancel_mission(mission_id):
        return jsonify({
            "success": True,
            "message": f"미션 {mission_id}이(가) 취소되었습니다."
        }), 200
    return jsonify({
        "success": False,
        "message": f"미션 {mission_id} 취소 실패"
    }), 500 