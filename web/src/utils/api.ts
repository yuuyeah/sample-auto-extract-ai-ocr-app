import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

// 環境変数からAPIのベースURLを取得
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

// URLが正しい形式であることを確認
const ensureHttps = (url: string) => {
  if (!url) return '';
  // すでにhttps://で始まっている場合はそのまま返す
  if (url.startsWith('https://')) return url;
  // httpsプロトコルを追加
  return `https://${url}`;
};

const api = axios.create({
  baseURL: ensureHttps(apiBaseUrl),
});

// デバッグ用のログフラグ（本番環境では無効にする）
const enableDebugLogs = false;

// リクエストインターセプター
api.interceptors.request.use(
  async (config) => {
    try {
      const { tokens } = await fetchAuthSession();
      const idToken = tokens?.idToken?.toString();

      if (idToken) {
        config.headers.Authorization = `Bearer ${idToken}`;
      } else if (enableDebugLogs) {
        console.warn("認証トークンが取得できません");
      }
      
      if (enableDebugLogs) {
        console.log('API Request:', {
          url: config.url,
          baseURL: config.baseURL,
          fullURL: `${config.baseURL}${config.url}`,
          method: config.method
        });
      }
    } catch (error) {
      if (enableDebugLogs) {
        console.error("認証トークン取得エラー:", error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// レスポンスインターセプター
api.interceptors.response.use(
  (response) => {
    if (enableDebugLogs) {
      console.log('API Response Success:', {
        status: response.status,
        url: response.config.url
      });
    }
    return response;
  },
  (error) => {
    if (enableDebugLogs) {
      if (error.response) {
        console.error('API Error:', error.response.status, error.response.data);
      } else if (error.request) {
        console.error('API Request Error:', error.request);
      } else {
        console.error('API Config Error:', error.message);
      }
    }
    return Promise.reject(error);
  }
);

// Agent API
export const runAgent = async (imageId: string) => {
  // Start agent job
  const startResponse = await api.post(`/ocr/agent/${imageId}`);
  const jobId = startResponse.data.jobId;
  
  // Poll for completion
  return pollAgentJobStatus(jobId);
};

export const pollAgentJobStatus = async (
  jobId: string,
  maxAttempts = 60,
  interval = 2000
): Promise<any> => {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const response = await api.get(`/ocr/agent/status/${jobId}`);
    const { status, suggestions, error } = response.data;
    
    if (status === 'completed') {
      return { status: 'success', suggestions };
    }
    
    if (status === 'failed') {
      throw new Error(error || 'Agent processing failed');
    }
    
    // Wait before next poll
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
  
  throw new Error('Agent processing timed out');
};

export const getAgentTools = async () => {
  const response = await api.get('/ocr/agent/tools');
  return response.data;
};

export default api;
