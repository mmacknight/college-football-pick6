import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_POLL_INTERVAL = 60000; // 1 minute

export const usePolling = (pollFunction, interval = DEFAULT_POLL_INTERVAL, enabled = true) => {
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  
  const intervalRef = useRef(null);
  const isEnabledRef = useRef(enabled);
  
  // Update enabled ref when prop changes
  useEffect(() => {
    isEnabledRef.current = enabled;
  }, [enabled]);

  const startPolling = useCallback(() => {
    console.log('🎯 startPolling called');
    
    if (intervalRef.current) {
      console.log('🔄 Clearing existing interval');
      clearInterval(intervalRef.current);
    }
    
    setIsPolling(true);
    setError(null);
    
    const poll = async () => {
      if (!isEnabledRef.current) {
        console.log('🔄 Polling skipped - disabled');
        return;
      }
      
      console.log('🔄 Executing poll function...');
      try {
        const result = await pollFunction();
        setLastUpdate(new Date().toISOString());
        setError(null);
        console.log('✅ Poll completed successfully');
      } catch (err) {
        console.error('❌ Polling error:', err);
        setError(err.message || 'Polling failed');
      }
    };
    
    // Poll immediately, then set interval
    console.log('🔄 Starting immediate poll...');
    poll();
    console.log(`⏰ Setting interval for ${interval}ms`);
    intervalRef.current = setInterval(poll, interval);
    console.log('✅ Polling started successfully');
  }, [pollFunction, interval]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Auto start/stop based on enabled prop
  useEffect(() => {
    console.log('🔍 usePolling useEffect - enabled:', enabled);
    if (enabled) {
      console.log('🚀 Starting polling...');
      startPolling();
    } else {
      console.log('⏸️ Stopping polling...');
      stopPolling();
    }
    
    // Cleanup on unmount
    return () => {
      console.log('🧹 Cleaning up polling...');
      stopPolling();
    };
  }, [enabled, startPolling, stopPolling]);

  return {
    isPolling,
    error,
    lastUpdate,
    startPolling,
    stopPolling
  };
};
