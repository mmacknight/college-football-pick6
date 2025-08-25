import { useEffect, useRef, useCallback, useState } from 'react';
import websocketService from '../services/websocketService';

/**
 * React hook for WebSocket integration
 * 
 * Usage examples:
 * 
 * // Basic subscription
 * const { isConnected, send } = useWebSocket('draft_update', (data) => {
 *   console.log('Draft updated:', data);
 * });
 * 
 * // Multiple subscriptions
 * const { isConnected } = useWebSocket([
 *   ['draft_update', handleDraftUpdate],
 *   ['score_update', handleScoreUpdate],
 *   ['league_update', handleLeagueUpdate]
 * ]);
 * 
 * // Connection state monitoring
 * const { isConnected, connectionState } = useWebSocket();
 */
export function useWebSocket(subscriptions = null, options = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState('DISCONNECTED');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const unsubscribeFunctionsRef = useRef([]);
  
  const {
    autoConnect = true,
    onConnected = null,
    onDisconnected = null,
    onError = null,
    onReconnecting = null
  } = options;

  // Normalize subscriptions to array format
  const normalizedSubscriptions = useRef([]);
  useEffect(() => {
    if (!subscriptions) {
      normalizedSubscriptions.current = [];
    } else if (typeof subscriptions === 'string') {
      // Single subscription with no callback
      normalizedSubscriptions.current = [[subscriptions, null]];
    } else if (Array.isArray(subscriptions)) {
      if (subscriptions.length === 2 && typeof subscriptions[0] === 'string') {
        // Single subscription: ['type', callback]
        normalizedSubscriptions.current = [subscriptions];
      } else {
        // Multiple subscriptions: [['type1', callback1], ['type2', callback2]]
        normalizedSubscriptions.current = subscriptions;
      }
    }
  }, [subscriptions]);

  // Setup connection state listeners
  useEffect(() => {
    const updateConnectionState = () => {
      const state = websocketService.getState();
      setConnectionState(state);
      setIsConnected(state === 'CONNECTED');
    };

    // Initial state
    updateConnectionState();

    // Set up callbacks
    const originalOnConnected = websocketService.onConnected;
    const originalOnDisconnected = websocketService.onDisconnected;
    const originalOnError = websocketService.onError;
    const originalOnReconnecting = websocketService.onReconnecting;

    websocketService.onConnected = () => {
      updateConnectionState();
      if (onConnected) onConnected();
      if (originalOnConnected) originalOnConnected();
    };

    websocketService.onDisconnected = (event) => {
      updateConnectionState();
      if (onDisconnected) onDisconnected(event);
      if (originalOnDisconnected) originalOnDisconnected(event);
    };

    websocketService.onError = (error) => {
      updateConnectionState();
      if (onError) onError(error);
      if (originalOnError) originalOnError(error);
    };

    websocketService.onReconnecting = (attempts) => {
      setReconnectAttempts(attempts);
      if (onReconnecting) onReconnecting(attempts);
      if (originalOnReconnecting) originalOnReconnecting(attempts);
    };

    return () => {
      // Restore original callbacks
      websocketService.onConnected = originalOnConnected;
      websocketService.onDisconnected = originalOnDisconnected;
      websocketService.onError = originalOnError;
      websocketService.onReconnecting = originalOnReconnecting;
    };
  }, [onConnected, onDisconnected, onError, onReconnecting]);

  // Setup subscriptions
  useEffect(() => {
    // Clean up previous subscriptions
    unsubscribeFunctionsRef.current.forEach(unsubscribe => unsubscribe());
    unsubscribeFunctionsRef.current = [];

    // Set up new subscriptions
    normalizedSubscriptions.current.forEach(([type, callback]) => {
      if (callback) {
        const unsubscribe = websocketService.subscribe(type, callback);
        unsubscribeFunctionsRef.current.push(unsubscribe);
      }
    });

    return () => {
      // Clean up on unmount
      unsubscribeFunctionsRef.current.forEach(unsubscribe => unsubscribe());
      unsubscribeFunctionsRef.current = [];
    };
  }, [normalizedSubscriptions.current]);

  // Auto-connect if enabled and user is authenticated
  useEffect(() => {
    if (autoConnect && !websocketService.isConnected()) {
      const token = localStorage.getItem('pick6_token'); // Fixed: use correct token key
      if (token) {
        const baseUrl = process.env.NODE_ENV === 'development' 
          ? 'http://localhost:3001' 
          : 'https://your-api-domain.com';
        
        console.log('🔌 Attempting WebSocket connection with token:', token ? 'present' : 'missing');
        websocketService.connect(token, baseUrl).catch(error => {
          console.error('Failed to connect WebSocket:', error);
        });
      } else {
        console.log('🔌 No auth token found, skipping WebSocket connection');
      }
    }
  }, [autoConnect]);

  // Send message function
  const send = useCallback((type, data) => {
    return websocketService.send(type, data);
  }, []);

  // Connect function
  const connect = useCallback((token, baseUrl) => {
    return websocketService.connect(token, baseUrl);
  }, []);

  // Disconnect function
  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  // Subscribe function for dynamic subscriptions
  const subscribe = useCallback((type, callback) => {
    return websocketService.subscribe(type, callback);
  }, []);

  // Unsubscribe function
  const unsubscribe = useCallback((type, callback) => {
    websocketService.unsubscribe(type, callback);
  }, []);

  return {
    isConnected,
    connectionState,
    reconnectAttempts,
    send,
    connect,
    disconnect,
    subscribe,
    unsubscribe
  };
}

/**
 * Hook for subscribing to a single message type
 */
export function useWebSocketSubscription(type, callback, dependencies = []) {
  const { isConnected } = useWebSocket();
  
  useEffect(() => {
    if (!callback) return;
    
    const unsubscribe = websocketService.subscribe(type, callback);
    return unsubscribe;
  }, [type, ...dependencies]);

  return { isConnected };
}

/**
 * Hook for sending WebSocket messages
 */
export function useWebSocketSender() {
  const send = useCallback((type, data) => {
    return websocketService.send(type, data);
  }, []);

  return send;
}

export default useWebSocket;
