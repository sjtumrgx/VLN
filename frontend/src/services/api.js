const BASE_URL = '/api';

export const api = {
  async createTask(instruction) {
    const res = await fetch(`${BASE_URL}/tasks/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instruction }),
    });
    if (!res.ok) throw new Error('创建任务失败');
    return res.json();
  },

  async getTask(taskId) {
    const res = await fetch(`${BASE_URL}/tasks/${taskId}`);
    if (!res.ok) throw new Error('获取任务失败');
    return res.json();
  },

  async listTasks(limit = 50) {
    const res = await fetch(`${BASE_URL}/tasks/list?limit=${limit}`);
    if (!res.ok) throw new Error('获取任务列表失败');
    return res.json();
  },

  async getTaskHistory(taskId) {
    const res = await fetch(`${BASE_URL}/tasks/${taskId}/history`);
    if (!res.ok) throw new Error('获取历史失败');
    return res.json();
  },

  async updateTask(taskId, updates) {
    const res = await fetch(`${BASE_URL}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('更新任务失败');
    return res.json();
  },

  async getModelStatus() {
    const res = await fetch(`${BASE_URL}/models/status`);
    if (!res.ok) throw new Error('获取模型状态失败');
    return res.json();
  },

  async listModels() {
    const res = await fetch(`${BASE_URL}/models/list`);
    if (!res.ok) throw new Error('获取模型列表失败');
    return res.json();
  },
};
