import express from 'express';
import path from 'path';
import fs from 'fs';
import multer from 'multer';
import { createServer as createViteServer } from 'vite';
import { db, initDatabase } from './db.js';

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 8080;

  // JSON and URL-encoded body parsing
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  // Auto-create uploads directory structure
  const uploadsDir = path.join(process.cwd(), 'uploads');
  const projetosDir = path.join(uploadsDir, 'projetos');
  const timelineDir = path.join(uploadsDir, 'timeline');
  const equipeDir = path.join(uploadsDir, 'equipe');
  const siteAssetsDir = path.join(uploadsDir, 'site-assets');

  [uploadsDir, projetosDir, timelineDir, equipeDir, siteAssetsDir].forEach((dir) => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  // Expose uploads as a static folder
  app.use('/uploads', express.static(uploadsDir));

  // Connect & Migrate Database
  await initDatabase();

  // Simple Auth token check middleware
  const SECRET_ACCESS_TOKEN = 'eme-moveis-secret-super-auth-token-key-2026';
  
  const authenticateAdmin = (req: express.Request, res: express.Response, next: express.NextFunction) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Não autorizado. Faça login novamente.' });
    }
    const token = authHeader.split(' ')[1];
    if (token === SECRET_ACCESS_TOKEN) {
      next();
    } else {
      return res.status(403).json({ error: 'Token inválido ou expirado.' });
    }
  };

  // Multer Storage Configuration
  const storage = multer.diskStorage({
    destination: (req, file, cb) => {
      // Determine folder based on request query param: ?folder=projetos, ?folder=timeline, etc.
      const folderParam = req.query.folder as string;
      let targetDir = projectsDestination(folderParam, projetosDir, timelineDir, equipeDir, siteAssetsDir);
      cb(null, targetDir);
    },
    filename: (req, file, cb) => {
      const ext = path.extname(file.originalname);
      const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
      cb(null, `${file.fieldname}-${uniqueSuffix}${ext}`);
    }
  });

  const upload = multer({ storage });

  // API 1: Authentication Endpoint
  app.post('/api/auth/login', async (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ error: 'Usuário e senha são obrigatórios.' });
    }
    try {
      const user = await db.verifyUser(username, password);
      if (user) {
        return res.json({
          success: true,
          token: SECRET_ACCESS_TOKEN,
          user: { id: user.id, username: user.username }
        });
      } else {
        return res.status(401).json({ error: 'Usuário ou senha incorretos.' });
      }
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 1.5: Update Admin Credentials
  app.post('/api/auth/update-credentials', authenticateAdmin, async (req, res) => {
    const { username, password } = req.body;
    if (!username) {
      return res.status(400).json({ error: 'O nome de usuário é obrigatório.' });
    }
    try {
      const success = await (db as any).updateAdminUser(username, password || undefined);
      if (success) {
        return res.json({ success: true, message: 'Credenciais de administrador alteradas com sucesso.' });
      } else {
        return res.status(404).json({ error: 'Administrador não encontrado.' });
      }
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 2: Image Upload Process
  app.post('/api/upload', authenticateAdmin, upload.single('file'), (req, res) => {
    if (!req.file) {
      return res.status(400).json({ error: 'Nenhum arquivo enviado.' });
    }
    const folderParam = (req.query.folder as string) || 'projetos';
    // Return relative public path (e.g. /uploads/projetos/filename.jpg)
    const filePath = `/uploads/${folderParam}/${req.file.filename}`;
    return res.json({ success: true, filePath });
  });

  // API 3: Projects GET
  app.get('/api/projects', async (req, res) => {
    try {
      const projects = await db.getProjects();
      return res.json(projects);
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 3: Projects POST (Create)
  app.post('/api/projects', authenticateAdmin, async (req, res) => {
    const { title, description, category, image, album } = req.body;
    if (!title || !category || !image) {
      return res.status(400).json({ error: 'Título, Categoria e Imagem são obrigatórios.' });
    }
    try {
      const newProject = await db.addProject({ title, description, category, image, album });
      return res.status(211).json(newProject);
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 3: Projects PUT (Update)
  app.put('/api/projects/:id', authenticateAdmin, async (req, res) => {
    const id = parseInt(req.params.id, 10);
    const { title, description, category, image, album } = req.body;
    if (!title || !category || !image) {
      return res.status(400).json({ error: 'Título, Categoria e Imagem são obrigatórios.' });
    }
    try {
      const success = await db.updateProject(id, { title, description, category, image, album });
      if (success) {
        return res.json({ success: true, message: 'Projeto atualizado com sucesso.' });
      } else {
        return res.status(404).json({ error: 'Projeto não encontrado.' });
      }
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 3: Projects DELETE
  app.delete('/api/projects/:id', authenticateAdmin, async (req, res) => {
    const id = parseInt(req.params.id, 10);
    try {
      const success = await db.deleteProject(id);
      if (success) {
        return res.json({ success: true, message: 'Projeto excluído com sucesso.' });
      } else {
        return res.status(404).json({ error: 'Projeto não encontrado.' });
      }
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 4: Timeline GET
  app.get('/api/timeline', async (req, res) => {
    try {
      const list = await db.getTimeline();
      return res.json(list);
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 4: Timeline POST (Create)
  app.post('/api/timeline', authenticateAdmin, async (req, res) => {
    const { year, title, description, image } = req.body;
    if (!year || !title || !description) {
      return res.status(400).json({ error: 'Ano, Título e Descrição são obrigatórios.' });
    }
    try {
      const newItem = await db.addTimeline({ year, title, description, image });
      return res.status(211).json(newItem);
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 4: Timeline PUT (Update)
  app.put('/api/timeline/:id', authenticateAdmin, async (req, res) => {
    const id = parseInt(req.params.id, 10);
    const { year, title, description, image } = req.body;
    if (!year || !title || !description) {
      return res.status(400).json({ error: 'Ano, Título e Descrição são obrigatórios.' });
    }
    try {
      const success = await db.updateTimeline(id, { year, title, description, image });
      if (success) {
        return res.json({ success: true, message: 'Item da linha do tempo atualizado.' });
      } else {
        return res.status(404).json({ error: 'Item não encontrado.' });
      }
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 4: Timeline DELETE
  app.delete('/api/timeline/:id', authenticateAdmin, async (req, res) => {
    const id = parseInt(req.params.id, 10);
    try {
      const success = await db.deleteTimeline(id);
      if (success) {
        return res.json({ success: true, message: 'Item excluído com sucesso.' });
      } else {
        return res.status(404).json({ error: 'Item não encontrado.' });
      }
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 5: Settings GET
  app.get('/api/settings', async (req, res) => {
    try {
      const settings = await db.getSettings();
      return res.json(settings);
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // API 5: Settings POST (Update)
  app.post('/api/settings', authenticateAdmin, async (req, res) => {
    const { heroImage, aboutImage } = req.body;
    try {
      await db.updateSettings({ heroImage, aboutImage });
      return res.json({ success: true, message: 'Configurações atualizadas com sucesso.' });
    } catch (e: any) {
      return res.status(500).json({ error: e.message });
    }
  });

  // Vite development middleware setup (serves standard index.html on secondary routing)
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  // Bind to port 3000 and host 0.0.0.0
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Express server running on http://0.0.0.0:${PORT}`);
  });
}

function projectsDestination(folderParam: string, projetosDir: string, timelineDir: string, equipeDir: string, siteAssetsDir: string): string {
  if (folderParam === 'timeline') {
    return timelineDir;
  }
  if (folderParam === 'equipe') {
    return equipeDir;
  }
  if (folderParam === 'site-assets') {
    return siteAssetsDir;
  }
  return projetosDir;
}

startServer();
