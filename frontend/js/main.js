import { getTasks, createTask } from './api.js';

document.addEventListener("DOMContentLoaded", async () => {
    const tasks = await getTasks();
    const taskList = document.querySelector("#task-list");
    tasks.forEach(task => {
        const li = document.createElement("li");
        li.textContent = `${task.name} (Priority: ${task.priority}, Status: ${task.status})`;
        taskList.appendChild(li);
    });
});
