tasks = []

class Task:
    def __init__(self, id, name, priority, status):
        self.id = id
        self.name = name
        self.priority = priority
        self.status = status
    def to_dict(self):
        return vars(self)
    @classmethod
    def get_all(cls):
        return tasks
    @classmethod
    def create(cls, data):
        task = Task(len(tasks) + 1, data['name'], data['priority'], 'pending')
        tasks.append(task)
        return task
    @classmethod
    def get(cls, task_id):
        return next((t for t in tasks if t.id == task_id), None)
