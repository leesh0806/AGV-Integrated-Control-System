from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import random

# 로그 관련 API 블루프린트 생성
log_api = Blueprint('log_api', __name__)

# 임시 로그 데이터 저장소 (실제 프로덕션에서는 데이터베이스 사용)
DUMMY_LOGS = []

# 로그 레벨
LOG_LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]

# 로그 소스
LOG_SOURCES = ["SYSTEM", "NETWORK", "TRUCK_CONTROL", "MISSION_MANAGEMENT", "USER_AUTH"]

# 초기 더미 로그 생성
def generate_dummy_logs(count=50):
    """테스트용 더미 로그 생성"""
    logs = []
    now = datetime.now()
    
    messages = [
        "시스템 시작됨",
        "트럭 연결 성공",
        "트럭 연결 실패",
        "미션 생성됨",
        "미션 완료됨",
        "미션 취소됨",
        "게이트 열림",
        "게이트 닫힘",
        "배터리 부족 경고",
        "네트워크 연결 끊김",
        "네트워크 연결 복구됨",
        "사용자 로그인 성공",
        "사용자 로그인 실패",
        "시스템 종료"
    ]
    
    for i in range(count):
        timestamp = now - timedelta(minutes=random.randint(0, 60*24*7))  # 최대 1주일 전 로그
        level = random.choice(LOG_LEVELS)
        source = random.choice(LOG_SOURCES)
        message = random.choice(messages)
        
        logs.append({
            "id": str(i+1),
            "timestamp": timestamp.isoformat(),
            "level": level,
            "source": source,
            "message": message
        })
    
    # 최신 로그 기준으로 정렬
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs

# 초기 더미 로그 생성
DUMMY_LOGS = generate_dummy_logs()

# ------------------ 로그 API ----------------------------

@log_api.route("/logs", methods=["GET"])
def get_logs():
    """로그 조회 (필터링 가능)"""
    # 필터 파라미터 가져오기
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    level = request.args.get("level")
    source = request.args.get("source")
    keyword = request.args.get("keyword")
    
    # 필터링
    filtered_logs = DUMMY_LOGS
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log["timestamp"]) >= start]
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            filtered_logs = [log for log in filtered_logs if datetime.fromisoformat(log["timestamp"]) <= end]
        except ValueError:
            pass
    
    if level:
        filtered_logs = [log for log in filtered_logs if log["level"] == level]
    
    if source:
        filtered_logs = [log for log in filtered_logs if log["source"] == source]
    
    if keyword:
        filtered_logs = [log for log in filtered_logs if keyword.lower() in log["message"].lower()]
    
    # 응답 반환
    return jsonify({
        "success": True,
        "logs": filtered_logs
    })


@log_api.route("/logs/clear", methods=["POST"])
def clear_logs():
    """로그 삭제"""
    global DUMMY_LOGS
    
    # 필터 파라미터 가져오기
    data = request.json or {}
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    level = data.get("level")
    source = data.get("source")
    
    # 삭제할 로그 수 저장
    original_count = len(DUMMY_LOGS)
    
    # 조건에 맞는 로그 유지 (필터 조건에 맞는 로그는 삭제)
    remaining_logs = DUMMY_LOGS
    
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            remaining_logs = [
                log for log in remaining_logs 
                if not (start <= datetime.fromisoformat(log["timestamp"]) <= end)
            ]
        except ValueError:
            pass
    
    if level:
        remaining_logs = [log for log in remaining_logs if log["level"] != level]
    
    if source:
        remaining_logs = [log for log in remaining_logs if log["source"] != source]
    
    # 삭제된 로그 수 계산
    deleted_count = original_count - len(remaining_logs)
    
    # 로그 업데이트
    DUMMY_LOGS = remaining_logs
    
    # 응답 반환
    return jsonify({
        "success": True,
        "deleted_count": deleted_count
    }) 