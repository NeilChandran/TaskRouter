"""
TaskRouter - A Load-Balancing Task Scheduler

This project simulates a backend microservice for accepting and dispatching tasks across multiple workers using round-robin and priority-based scheduling. Useful for backend system design, concurrency handling, and demonstrating scalable software architecture.

Author: Internship Prep Toolkit
"""

import threading
import time
import random
from queue import PriorityQueue, Queue
from flask import Flask, request, jsonify
import logging
import uuid
import atexit
from collections import defaultdict
from datetime import datetime

# ----------------------------- Logging Setup -----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------------------- Task Utilities -----------------------------
def estimate_completion_time(duration):
    return datetime.utcnow() + timedelta(seconds=duration)

def validate_task_data(data):
    return isinstance(data.get("description"), str) and isinstance(data.get("duration"), int)

# ----------------------------- Task History Tracker -----------------------------
class TaskHistory:
    def __init__(self):
        self.completed_tasks = []
        self.failed_tasks = []
        self.execution_log = defaultdict(list)
        self.timestamps = []
        self.cancelled_tasks = []

    def add_completed(self, task):
        self.completed_tasks.append(task)
        self.execution_log[task['worker']].append(task)
        self.timestamps.append((task['id'], datetime.utcnow().isoformat()))

    def add_failed(self, task):
        self.failed_tasks.append(task)
        self.execution_log[task['worker']].append(task)
        self.timestamps.append((task['id'], datetime.utcnow().isoformat()))

    def add_cancelled(self, task_id):
        self.cancelled_tasks.append(task_id)

    def get_summary(self):
        return {
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "cancelled": len(self.cancelled_tasks),
            "last_10_timestamps": self.timestamps[-10:]
        }

    def get_all_tasks(self):
        return {
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "cancelled": self.cancelled_tasks
        }

    def get_worker_log(self, worker_id):
        return self.execution_log.get(worker_id, [])

    def get_most_recent_task(self):
        if self.timestamps:
            return self.timestamps[-1]
        return None

history = TaskHistory()

# ----------------------------- Worker Definition -----------------------------
class Worker(threading.Thread):
    def __init__(self, worker_id, task_queue):
        super().__init__()
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.daemon = True
        self.active = True
        self.task_count = 0

    def run(self):
        while self.active:
            try:
                priority, task = self.task_queue.get(timeout=2)
                task['worker'] = f"Worker-{self.worker_id}"
                logging.info(f"Worker-{self.worker_id} started task: {task['id']}")
                try:
                    time.sleep(task['duration'])
                    logging.info(f"Worker-{self.worker_id} completed task: {task['id']}")
                    history.add_completed(task)
                    self.task_count += 1
                except Exception as e:
                    logging.error(f"Task {task['id']} failed: {e}")
                    history.add_failed(task)
                self.task_queue.task_done()
            except Exception:
                continue

    def stop(self):
        self.active = False

# ----------------------------- Scheduler Definition -----------------------------
class Scheduler:
    def __init__(self, num_workers=4, mode="priority"):
        self.num_workers = num_workers
        self.mode = mode
        self.task_queue = PriorityQueue() if mode == "priority" else Queue()
        self.workers = [Worker(i, self.task_queue) for i in range(num_workers)]
        self.task_registry = {}

    def start(self):
        for worker in self.workers:
            worker.start()
        logging.info("All workers started.")

    def stop(self):
        for worker in self.workers:
            worker.stop()

    def submit_task(self, task):
        self.task_registry[task['id']] = task
        if self.mode == "priority":
            priority = task.get("priority", 5)
            self.task_queue.put((priority, task))
        else:
            self.task_queue.put(task)

    def cancel_task(self, task_id):
        if task_id in self.task_registry:
            history.add_cancelled(task_id)
            del self.task_registry[task_id]
            return True
        return False

    def queue_size(self):
        return self.task_queue.qsize()

    def active_workers(self):
        return sum(1 for w in self.workers if w.is_alive())

    def worker_ids(self):
        return [f"Worker-{i}" for i in range(self.num_workers)]

    def worker_task_counts(self):
        return {f"Worker-{w.worker_id}": w.task_count for w in self.workers}

# ----------------------------- Flask API -----------------------------
app = Flask(__name__)
scheduler = Scheduler(num_workers=4, mode="priority")
scheduler.start()

@app.route('/submit', methods=['POST'])
def submit_task():
    data = request.get_json()
    if not validate_task_data(data):
        return jsonify({"error": "Invalid task data."}), 400

    task = {
        'id': str(uuid.uuid4()),
        'description': data.get('description', 'No description'),
        'duration': data.get('duration', random.randint(1, 5)),
        'priority': data.get('priority', 5)
    }
    scheduler.submit_task(task)
    return jsonify({"status": "Task submitted", "task_id": task['id']}), 200

@app.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    success = scheduler.cancel_task(task_id)
    if success:
        return jsonify({"status": f"Task {task_id} cancelled."}), 200
    return jsonify({"error": "Task not found."}), 404

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "queue_size": scheduler.queue_size(),
        "active_workers": scheduler.active_workers(),
        "worker_task_counts": scheduler.worker_task_counts()
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(history.get_summary()), 200

@app.route('/history/all', methods=['GET'])
def get_all_history():
    return jsonify(history.get_all_tasks()), 200

@app.route('/worker/<worker_id>', methods=['GET'])
def worker_log(worker_id):
    return jsonify({"worker_id": worker_id, "log": history.get_worker_log(worker_id)}), 200

@app.route('/workers', methods=['GET'])
def get_workers():
    return jsonify({"workers": scheduler.worker_ids()}), 200

@app.route('/history/recent', methods=['GET'])
def get_recent_task():
    recent = history.get_most_recent_task()
    return jsonify({"recent_task": recent}), 200

@app.route('/submit/batch', methods=['POST'])
def submit_batch():
    data = request.get_json()
    count = data.get("count", 5)
    for i in range(count):
        task = {
            'id': str(uuid.uuid4()),
            'description': f"Batch Task {i}",
            'duration': random.randint(1, 3),
            'priority': random.randint(1, 10)
        }
        scheduler.submit_task(task)
    return jsonify({"status": f"Submitted {count} tasks."}), 200

# ----------------------------- Testing Utilities -----------------------------
def submit_test_tasks():
    for i in range(10):
        task = {
            "id": str(uuid.uuid4()),
            "description": f"Test Task {i}",
            "duration": random.randint(1, 3),
            "priority": random.randint(1, 10)
        }
        scheduler.submit_task(task)
        logging.info(f"Submitted: {task}")
        time.sleep(0.2)

# ----------------------------- Extra Utilities -----------------------------
def graceful_shutdown():
    logging.info("Shutting down all workers...")
    scheduler.stop()
    for worker in scheduler.workers:
        worker.join()
    logging.info("Shutdown complete.")

atexit.register(graceful_shutdown)

# ----------------------------- Entry Point -----------------------------
if __name__ == '__main__':
    try:
        app.run(port=5000, debug=False)
    except KeyboardInterrupt:
        graceful_shutdown()
@app.route('/metrics', methods=['GET'])
def get_metrics():
    metrics = {
        "total_tasks": len(history.completed_tasks) + len(history.failed_tasks) + len(history.cancelled_tasks),
        "completed": len(history.completed_tasks),
        "failed": len(history.failed_tasks),
        "cancelled": len(history.cancelled_tasks),
        "active_workers": scheduler.active_workers(),
        "queue_size": scheduler.queue_size(),
    }
    return jsonify(metrics), 200

@app.route('/reset', methods=['POST'])
def reset_system():
    history.completed_tasks.clear()
    history.failed_tasks.clear()
    history.cancelled_tasks.clear()
    history.execution_log.clear()
    history.timestamps.clear()
    logging.info("System reset complete.")
    return jsonify({"status": "System reset."}), 200


@app.route('/task/<task_id>', methods=['GET'])
def get_task_by_id(task_id):
    task = scheduler.task_registry.get(task_id)
    if task:
        return jsonify(task), 200
    return jsonify({"error": "Task not found."}), 404

@app.route('/pause', methods=['POST'])
def pause_workers():
    for worker in scheduler.workers:
        worker.active = False
    return jsonify({"status": "All workers paused."}), 200

@app.route('/resume', methods=['POST'])
def resume_workers():
    for worker in scheduler.workers:
        worker.active = True
    return jsonify({"status": "All workers resumed."}), 200


