export async function getTasks() {
    const res = await fetch('/api/tasks/');
    return await res.json();
}

export async function createTask(task) {
    const res = await fetch('/api/tasks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json'},
        body: JSON.stringify(task)
    });
    return await res.json();
}
