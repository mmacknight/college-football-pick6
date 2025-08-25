// Configuration for different environments
const config = {
  development: {
    API_BASE_URL: 'http://localhost:3001',
    WEBSOCKET_URL: 'ws://localhost:3002'
  },
  production: {
    API_BASE_URL: window.location.origin,
    WEBSOCKET_URL: `wss://${window.location.host}/ws`
  }
};

// Determine current environment
const getEnvironment = () => {
  if (typeof window !== 'undefined') {
    return window.location.hostname === 'localhost' ? 'development' : 'production';
  }
  return 'development';
};

const currentEnv = getEnvironment();
const currentConfig = config[currentEnv];

export default currentConfig;
