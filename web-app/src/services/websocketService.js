/**
 * Robust Socket.IO Service for Real-time Updates
 * 
 * Handles all real-time communication for the app:
 * - Draft updates
 * - Game scores
 * - League changes
 * - User notifications
 */

import { io } from 'socket.io-client';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.url = null;
    this.token = null;
    this.isConnecting = false;
    this.isManuallyDisconnected = false;
    
    // Event listeners by type
    this.listeners = new Map();
    
    // Connection state callbacks
    this.onConnected = null;
    this.onDisconnected = null;
    this.onError = null;
    this.onReconnecting = null;
  }

  /**
   * Initialize Socket.IO connection
   * @param {string} token - JWT token for authentication
   * @param {string} baseUrl - Base URL (http://localhost:3001 or https://api.example.com)
   */
  connect(token, baseUrl = 'http://localhost:3001') {
    if (this.isConnecting || (this.socket && this.socket.connected)) {
      console.log('🔌 Socket already connected or connecting');
      return Promise.resolve();
    }

    console.log('🔌 Starting Socket.IO connection to:', baseUrl);
    this.token = token;
    this.isManuallyDisconnected = false;
    
    return this._connect(baseUrl, token);
  }

  /**
   * Internal connection method
   */
  _connect(baseUrl, token) {
    return new Promise((resolve, reject) => {
      try {
        this.isConnecting = true;
        
        // Create Socket.IO connection
        this.socket = io(baseUrl, {
          auth: {
            token: token
          },
          query: {
            token: token
          },
          transports: ['websocket', 'polling'],
          upgrade: true,
          rememberUpgrade: true
        });

        // Connection opened
        this.socket.on('connect', () => {
          console.log('✅ Socket.IO connected');
          this.isConnecting = false;
          
          if (this.onConnected) {
            this.onConnected();
          }
          
          resolve();
        });

        // Connection error
        this.socket.on('connect_error', (error) => {
          console.error('❌ Socket.IO connection error:', error);
          this.isConnecting = false;
          
          if (this.onError) {
            this.onError(error);
          }
          
          reject(error);
        });

        // Connection closed
        this.socket.on('disconnect', (reason) => {
          console.log('🔌 Socket.IO disconnected:', reason);
          this.isConnecting = false;
          
          if (this.onDisconnected) {
            this.onDisconnected({ reason });
          }
        });

        // Reconnection attempt
        this.socket.on('reconnect_attempt', (attemptNumber) => {
          console.log(`🔄 Socket.IO reconnection attempt ${attemptNumber}`);
          if (this.onReconnecting) {
            this.onReconnecting(attemptNumber);
          }
        });

        // Setup existing listeners on new connection
        this._setupMessageListeners();

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect Socket.IO
   */
  disconnect() {
    this.isManuallyDisconnected = true;
    
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  /**
   * Send message to server
   * @param {string} type - Message type
   * @param {Object} data - Message data
   */
  send(type, data = {}) {
    if (!this.socket || !this.socket.connected) {
      console.warn('Socket.IO not connected, cannot send message');
      return false;
    }

    try {
      this.socket.emit(type, data);
      return true;
    } catch (error) {
      console.error('Failed to send Socket.IO message:', error);
      return false;
    }
  }

  /**
   * Subscribe to specific message types
   * @param {string} type - Message type to listen for
   * @param {Function} callback - Callback function
   */
  subscribe(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    
    this.listeners.get(type).add(callback);
    
    // Add listener to socket if connected
    if (this.socket) {
      this.socket.on(type, callback);
    }
    
    // Return unsubscribe function
    return () => {
      const typeListeners = this.listeners.get(type);
      if (typeListeners) {
        typeListeners.delete(callback);
        if (typeListeners.size === 0) {
          this.listeners.delete(type);
        }
      }
      
      // Remove from socket
      if (this.socket) {
        this.socket.off(type, callback);
      }
    };
  }

  /**
   * Unsubscribe from message type
   * @param {string} type - Message type
   * @param {Function} callback - Callback function (optional, removes all if not provided)
   */
  unsubscribe(type, callback = null) {
    if (!this.listeners.has(type)) return;
    
    if (callback) {
      this.listeners.get(type).delete(callback);
      if (this.socket) {
        this.socket.off(type, callback);
      }
    } else {
      this.listeners.delete(type);
      if (this.socket) {
        this.socket.removeAllListeners(type);
      }
    }
  }

  /**
   * Setup message listeners on socket
   */
  _setupMessageListeners() {
    if (!this.socket) return;
    
    // Re-attach all existing listeners to the new socket connection
    this.listeners.forEach((callbacks, type) => {
      callbacks.forEach(callback => {
        this.socket.on(type, callback);
      });
    });
  }



  /**
   * Get current connection state
   */
  getState() {
    if (!this.socket) return 'DISCONNECTED';
    
    if (this.isConnecting) return 'CONNECTING';
    if (this.socket.connected) return 'CONNECTED';
    return 'DISCONNECTED';
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.socket && this.socket.connected;
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
export default websocketService;
