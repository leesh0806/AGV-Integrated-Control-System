from flask import Flask
import atexit
from backend.rest_api.routes.truck_api import truck_api
from backend.rest_api.routes.mission_api import mission_api 
from backend.rest_api.routes.facility_api import facility_api
from backend.rest_api.managers import cleanup_managers

# Flask 웹 서버 인스턴스 생성
app = Flask(__name__)

# 블루프린트 등록 - 모든 라우트에 '/api' 프리픽스 추가
app.register_blueprint(truck_api, url_prefix='/api')
app.register_blueprint(mission_api, url_prefix='/api')
app.register_blueprint(facility_api, url_prefix='/api')

# 애플리케이션 종료 시 리소스 정리 함수 등록
atexit.register(cleanup_managers)

# ------------------ 서버 시작 ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True) 