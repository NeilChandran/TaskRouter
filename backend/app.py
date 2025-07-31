from flask import Flask
from backend.api.tasks import tasks_bp
from backend.api.workers import workers_bp
from backend.api.logs import logs_bp

app = Flask(__name__)
app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
app.register_blueprint(workers_bp, url_prefix='/api/workers')
app.register_blueprint(logs_bp, url_prefix='/api/logs')

@app.route('/')
def index():
    return "<h1>TaskRouter Dashboard Backend</h1>"

if __name__ == "__main__":
    app.run(debug=True)
