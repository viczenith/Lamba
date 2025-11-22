/**
 * WebSocket Service
 * Real-time updates for multi-tenant dashboards
 */

const WebSocketService = (() => {
  let ws = null;
  let url = null;
  let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  let reconnectDelay = 3000;
  let listeners = {};
  let isConnecting = false;
  let isAuthenticated = false;
  let currentTenant = null;

  // Initialize WebSocket
  const init = (token, tenant = null) => {
    currentTenant = tenant;
    url = `${protocol}//${window.location.host}/ws/notifications/`;

    connect(token);
  };

  // Connect to WebSocket
  const connect = (token) => {
    if (isConnecting || ws?.readyState === WebSocket.OPEN) return;

    isConnecting = true;

    try {
      ws = new WebSocket(url);

      ws.addEventListener('open', () => {
        isConnecting = false;
        reconnectAttempts = 0;
        reconnectDelay = 3000;

        // Authenticate
        send({
          type: 'authenticate',
          token: token,
          tenant_id: currentTenant?.id
        });

        Toast.info('Connected to real-time updates', 2000);
        emit('connected');
      });

      ws.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'authenticated') {
            isAuthenticated = true;
            emit('authenticated', data);
          } else if (data.type === 'error') {
            handleError(data);
          } else {
            // Emit specific event
            emit(data.type, data);
          }
        } catch (error) {
          console.error('WebSocket message parse error:', error);
        }
      });

      ws.addEventListener('close', () => {
        isConnecting = false;
        isAuthenticated = false;
        emit('disconnected');

        // Attempt reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);

          setTimeout(() => {
            connect(token);
          }, reconnectDelay);

          reconnectDelay = Math.min(reconnectDelay * 2, 30000); // Exponential backoff
        } else {
          Toast.warning('Lost connection to real-time updates');
        }
      });

      ws.addEventListener('error', (error) => {
        isConnecting = false;
        console.error('WebSocket error:', error);
        emit('error', error);
      });
    } catch (error) {
      isConnecting = false;
      console.error('WebSocket connection failed:', error);
    }
  };

  // Send message
  const send = (data) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  };

  // Subscribe to event type
  const on = (eventType, callback) => {
    if (!listeners[eventType]) {
      listeners[eventType] = [];
    }
    listeners[eventType].push(callback);

    // Return unsubscribe function
    return () => {
      listeners[eventType] = listeners[eventType].filter(cb => cb !== callback);
    };
  };

  // Subscribe to event once
  const once = (eventType, callback) => {
    const unsubscribe = on(eventType, (data) => {
      callback(data);
      unsubscribe();
    });
    return unsubscribe;
  };

  // Emit event to listeners
  const emit = (eventType, data) => {
    if (listeners[eventType]) {
      listeners[eventType].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in listener for ${eventType}:`, error);
        }
      });
    }
  };

  // Handle errors
  const handleError = (data) => {
    console.error('WebSocket error:', data);

    if (data.code === 'UNAUTHORIZED') {
      isAuthenticated = false;
      emit('authentication_failed', data);
    } else if (data.code === 'INVALID_TENANT') {
      emit('tenant_invalid', data);
    } else {
      emit('error', data);
    }
  };

  // Subscribe to company events (Tenant Admin)
  const subscribeToCompany = (companyId) => {
    send({
      type: 'subscribe',
      channel: `company_${companyId}`
    });
  };

  // Subscribe to user events
  const subscribeToUser = (userId) => {
    send({
      type: 'subscribe',
      channel: `user_${userId}`
    });
  };

  // Subscribe to allocation events
  const subscribeToAllocation = (allocationId) => {
    send({
      type: 'subscribe',
      channel: `allocation_${allocationId}`
    });
  };

  // Subscribe to payment events
  const subscribeToPayment = (paymentId) => {
    send({
      type: 'subscribe',
      channel: `payment_${paymentId}`
    });
  };

  // Unsubscribe from channel
  const unsubscribe = (channel) => {
    send({
      type: 'unsubscribe',
      channel
    });
  };

  // Disconnect
  const disconnect = () => {
    if (ws) {
      ws.close();
      ws = null;
    }
    isAuthenticated = false;
    listeners = {};
  };

  // Get connection status
  const getStatus = () => ({
    connected: ws?.readyState === WebSocket.OPEN,
    authenticated: isAuthenticated,
    reconnectAttempts,
    readyState: ws?.readyState
  });

  return {
    init,
    connect,
    send,
    on,
    once,
    emit,
    subscribeToCompany,
    subscribeToUser,
    subscribeToAllocation,
    subscribeToPayment,
    unsubscribe,
    disconnect,
    getStatus
  };
})();

// Listen for common WebSocket events
document.addEventListener('DOMContentLoaded', () => {
  // Connection status indicator
  WebSocketService.on('connected', () => {
    console.log('WebSocket connected');
  });

  WebSocketService.on('disconnected', () => {
    console.log('WebSocket disconnected');
  });

  WebSocketService.on('authenticated', () => {
    console.log('WebSocket authenticated');
  });

  WebSocketService.on('authentication_failed', () => {
    Toast.error('Real-time authentication failed');
  });

  // Generic data updates
  WebSocketService.on('data_updated', (data) => {
    const event = new CustomEvent('data-updated', { detail: data });
    document.dispatchEvent(event);
  });

  WebSocketService.on('data_created', (data) => {
    const event = new CustomEvent('data-created', { detail: data });
    document.dispatchEvent(event);
  });

  WebSocketService.on('data_deleted', (data) => {
    const event = new CustomEvent('data-deleted', { detail: data });
    document.dispatchEvent(event);
  });

  // Listen for custom document events
  document.addEventListener('data-updated', (e) => {
    console.log('Data updated:', e.detail);
  });

  document.addEventListener('data-created', (e) => {
    console.log('Data created:', e.detail);
  });

  document.addEventListener('data-deleted', (e) => {
    console.log('Data deleted:', e.detail);
  });
});
