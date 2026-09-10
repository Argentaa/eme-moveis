import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { createProxyMiddleware } from 'http-proxy-middleware';

const FRONTEND_PORT = Number(process.env.PORT || 3000);
const FASTAPI_BASE_URL = (process.env.FASTAPI_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const FASTAPI_API_URL = FASTAPI_BASE_URL.endsWith('/api') ? FASTAPI_BASE_URL : `${FASTAPI_BASE_URL}/api`;

async function startServer() {
  const app = express();

  // Health check local
  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // Proxy all /api/* calls to FastAPI while the browser stays on the frontend host.
  app.use('/api', createProxyMiddleware({
    target: FASTAPI_API_URL,
    changeOrigin: true,
    xfwd: true,
  }));

  // Standard middlewares for non-proxied routes.
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Global Error Handler to prevent crash
  app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
    console.error('Unhandled Server Error:', err);
    res.status(500).json({ error: 'Erro interno no servidor' });
  });

  // Hot Module Replacement/Vite setup
  if (process.env.NODE_ENV !== 'production') {
    console.log('Spawning Vite in middleware Mode (Development)...');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    console.log('Serving production static build output...');
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(FRONTEND_PORT, '0.0.0.0', () => {
    console.log(`=========================================`);
    console.log(` EME MOVEIS - FRONTEND SERVER`);
    console.log(` Frontend: http://localhost:${FRONTEND_PORT}`);
    console.log(` API Proxy: /api -> ${FASTAPI_API_URL}`);
    console.log(` Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`=========================================`);
  });
}

startServer().catch((error) => {
  console.error('CRITICAL: Server failed to start:', error);
});
