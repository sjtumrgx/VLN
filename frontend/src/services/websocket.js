class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.listeners = {};
    this.reconnectInterval = 3000;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.clientId = this.generateClientId();
  }

  generateClientId() {
    return Math.random().toString(36).substring(2, 10);
  }

  connect() {
    const wsUrl = `${this.url}?client_id=${this.clientId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket 连接成功');
      this.reconnectAttempts = 0;
      this.emit('connected', { clientId: this.clientId });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data.type, data);
        this.emit('message', data);
      } catch (err) {
        console.error('解析消息失败:', err);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket 断开');
      this.emit('disconnected');

      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        setTimeout(() => this.connect(), this.reconnectInterval);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
      this.emit('error', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket 未连接，无法发送消息');
    }
  }

  sendVideoFrame(base64Frame, taskId, instruction) {
    this.send({
      type: 'video_frame',
      task_id: taskId,
      frame: base64Frame,
      instruction: instruction,
      timestamp: Date.now(),
    });
  }

  bindTask(taskId) {
    this.send({
      type: 'bind_task',
      task_id: taskId,
    });
  }

  ping() {
    this.send({
      type: 'ping',
    });
  }

  get isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

export default WebSocketClient;
