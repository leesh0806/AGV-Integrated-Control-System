"""
이 파일은 하위 호환성을 위해 유지됩니다.
실제 서버 구현은 app.py로 이동되었습니다.
"""

from backend.rest_api.app import app

# 하위 호환성을 위해 이전 서버 코드 포인트 유지
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
