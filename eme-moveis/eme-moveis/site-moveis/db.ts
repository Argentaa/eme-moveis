import mysql from 'mysql2/promise';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

export function hashPassword(password: string): string {
  return crypto.createHash('sha256').update(password).digest('hex');
}

const dbUrl = process.env.DATABASE_URL;
const mysqlHost = process.env.MYSQL_HOST;

let useMySQL = false;
let pool: mysql.Pool | null = null;

const FALLBACK_FILE = path.join(process.cwd(), 'db_fallback.json');

interface FallbackSchema {
  users: any[];
  projects: any[];
  timeline: any[];
  settings?: { heroImage: string; aboutImage: string };
}

const defaultData: FallbackSchema = {
  settings: {
    heroImage: '/images/banner-principal.jpg',
    aboutImage: '/images/sobre-nos.jpg'
  },
  users: [{ id: 1, username: 'admin', password: hashPassword('admin123') }],
  projects: [
    { id: 1, title: 'Cozinha Gourmet Anthracite', category: 'Cozinha', image: 'https://images.unsplash.com/photo-1556911223-e1534ecdb531?auto=format&fit=crop&q=80&w=1200', album: ['https://images.unsplash.com/photo-1556911223-e1534ecdb531?auto=format&fit=crop&q=80&w=1200','https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&q=80&w=1200','https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&q=80&w=1200'], description: 'Cozinha com acabamento em tons escuros, ilha central e ferragens alemãs de alta performance.' },
    { id: 2, title: 'Suíte Master Walk-in', category: 'Closet', image: 'https://images.unsplash.com/photo-1595428774751-267868770857?auto=format&fit=crop&q=80&w=1200', album: ['https://images.unsplash.com/photo-1595428774751-267868770857?auto=format&fit=crop&q=80&w=1200','https://images.unsplash.com/photo-1592075103427-4c4f346048d0?auto=format&fit=crop&q=80&w=1200'], description: 'Closet planejado com divisões inteligentes, iluminação em LED embutida e nichos para calçados.' },
    { id: 3, title: 'Home Office Executivo', category: 'Quarto', image: 'https://images.unsplash.com/photo-1518481612222-68bbe828ecd1?auto=format&fit=crop&q=80&w=1200', album: ['https://images.unsplash.com/photo-1518481612222-68bbe828ecd1?auto=format&fit=crop&q=80&w=1200','https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&q=80&w=1200'], description: 'Ambiente focado em produtividade com mesa em L, painéis ripados e armários para organização.' },
    { id: 4, title: 'Living Integrado', category: 'Sala', image: 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&q=80&w=1200', album: ['https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&q=80&w=1200','https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&q=80&w=1200'], description: 'Painel de TV com fundo em pedra e móveis suspensos em laca branca fosca.' },
    { id: 5, title: 'Adega Gourmet Climatizada', category: 'Adega', image: 'https://images.unsplash.com/photo-1560185007-c5ca9d2c014d?auto=format&fit=crop&q=80&w=1200', album: ['https://images.unsplash.com/photo-1560185007-c5ca9d2c014d?auto=format&fit=crop&q=80&w=1200'], description: 'Churrasqueira integrada com marcenaria naval e linda adega para vinhos selecionados.' },
    { id: 6, title: 'Banheiro Spa', category: 'Banheiro', image: 'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&q=80&w=1200', album: ['https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&q=80&w=1200'], description: 'Gabinete suspenso com gavetões e espelheira com moldura em metal.' }
  ],
  timeline: [
    { id: 1, year: '2022', title: 'Fundação da eMe Móveis', description: 'Nascimento da eMe Móveis no Rio Grande do Sul, com foco inicial em cozinhas planejadas e painéis.', image: 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&q=80&w=600' },
    { id: 2, year: '2023', title: 'Primeiro móvel produzido', description: 'Entrega do primeiro dormitório completo com ferragens telescópicas e iluminação integrada de alto padrão.', image: 'https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&q=80&w=600' },
    { id: 21, year: '2024', title: 'Sede e show-room próprio', description: 'Inauguração de nossa sede em Frederico Westphalen/RS, apresentando as últimas tendências em acabamentos e MDF premium.', image: 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=600' },
    { id: 3, year: '2026', title: 'Mais de 100 Projetos Entregues', description: 'Marca histórica de projetos entregues e clientes satisfeitos em nossa região, unindo qualidade e exclusividade.', image: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&q=80&w=600' }
  ]
};

if (dbUrl || mysqlHost) {
  try {
    pool = dbUrl
      ? mysql.createPool(dbUrl)
      : mysql.createPool({
          host: mysqlHost,
          port: process.env.MYSQL_PORT ? Number(process.env.MYSQL_PORT) : 3306,
          user: process.env.MYSQL_USER,
          password: process.env.MYSQL_PASSWORD,
          database: process.env.MYSQL_DATABASE,
          waitForConnections: true,
          connectionLimit: 10,
        });
    console.log('MySQL Pool initialized');
    useMySQL = true;
  } catch (error) {
    console.error('Failed to create MySQL pool, falling back to file DB:', error);
  }
} else {
  console.log('MySQL not configured. Using file database fallback at:', FALLBACK_FILE);
}

function parseAlbum(raw: any): string[] {
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') {
    try { const p = JSON.parse(raw); return Array.isArray(p) ? p : [raw]; } catch { return [raw]; }
  }
  return [];
}

function readFallback(): FallbackSchema {
  if (!fs.existsSync(FALLBACK_FILE)) {
    fs.writeFileSync(FALLBACK_FILE, JSON.stringify(defaultData, null, 2), 'utf-8');
    return defaultData;
  }
  try { return JSON.parse(fs.readFileSync(FALLBACK_FILE, 'utf-8')); }
  catch { return defaultData; }
}

function writeFallback(data: FallbackSchema) {
  fs.writeFileSync(FALLBACK_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

export async function initDatabase() {
  if (useMySQL && pool) {
    let connection: mysql.PoolConnection | null = null;
    try {
      const maxAttempts = 15;
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try { connection = await pool.getConnection(); break; }
        catch (err) {
          if (attempt === maxAttempts) throw err;
          console.log(`MySQL not ready, retrying (${attempt}/${maxAttempts})...`);
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
      if (!connection) throw new Error('Could not obtain MySQL connection');
      try {
        await connection.query(`CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL) ENGINE=InnoDB;`);
        await connection.query(`CREATE TABLE IF NOT EXISTS projects (id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(255) NOT NULL, description TEXT, category VARCHAR(50) NOT NULL, image TEXT NOT NULL, album JSON) ENGINE=InnoDB;`);
        await connection.query(`CREATE TABLE IF NOT EXISTS timeline (id INT AUTO_INCREMENT PRIMARY KEY, year VARCHAR(10) NOT NULL, title VARCHAR(255) NOT NULL, description TEXT, image TEXT) ENGINE=InnoDB;`);
        await connection.query(`CREATE TABLE IF NOT EXISTS settings (id INT AUTO_INCREMENT PRIMARY KEY, hero_image TEXT NOT NULL, about_image TEXT NOT NULL) ENGINE=InnoDB;`);

        const [userRes]: any = await connection.query('SELECT * FROM users WHERE username = ?', ['admin']);
        if (userRes.length === 0) {
          await connection.query('INSERT INTO users (username, password) VALUES (?, ?)', ['admin', hashPassword('admin123')]);
        }
        const [projectRes]: any = await connection.query('SELECT * FROM projects LIMIT 1');
        if (projectRes.length === 0) {
          for (const p of defaultData.projects) {
            await connection.query('INSERT INTO projects (id, title, description, category, image, album) VALUES (?, ?, ?, ?, ?, ?)', [p.id, p.title, p.description, p.category, p.image, JSON.stringify(p.album)]);
          }
        }
        const [timelineRes]: any = await connection.query('SELECT * FROM timeline LIMIT 1');
        if (timelineRes.length === 0) {
          for (const t of defaultData.timeline) {
            await connection.query('INSERT INTO timeline (id, year, title, description, image) VALUES (?, ?, ?, ?, ?)', [t.id, t.year, t.title, t.description || '', t.image]);
          }
        }
        const [settingsRes]: any = await connection.query('SELECT * FROM settings LIMIT 1');
        if (settingsRes.length === 0) {
          await connection.query('INSERT INTO settings (id, hero_image, about_image) VALUES (1, ?, ?)', ['/images/banner-principal.jpg', '/images/sobre-nos.jpg']);
        }
        console.log('MySQL configuration completed successfully.');
      } finally { connection.release(); }
    } catch (error) {
      console.error('MySQL error. Falling back to File DB:', error);
      useMySQL = false;
      readFallback();
    }
  } else { readFallback(); }
}

export const db = {
  getProjects: async (): Promise<any[]> => {
    if (useMySQL && pool) {
      try {
        const [rows]: any = await pool.query('SELECT * FROM projects ORDER BY id DESC');
        return rows.map((r: any) => ({ id: r.id, title: r.title, category: r.category, mainImage: r.image, album: parseAlbum(r.album), description: r.description }));
      } catch (err) { console.error('MySQL getProjects error:', err); }
    }
    return [...readFallback().projects].reverse();
  },
  addProject: async (project: { title: string; category: string; image: string; description: string; album?: string[] }): Promise<any> => {
    const album = project.album || [project.image];
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query('INSERT INTO projects (title, category, image, description, album) VALUES (?, ?, ?, ?, ?)', [project.title, project.category, project.image, project.description, JSON.stringify(album)]);
        return { id: result.insertId, title: project.title, category: project.category, mainImage: project.image, album, description: project.description };
      } catch (err) { console.error('MySQL addProject error:', err); }
    }
    const data = readFallback();
    const newId = data.projects.length > 0 ? Math.max(...data.projects.map(p => p.id)) + 1 : 1;
    const newProject = { id: newId, title: project.title, category: project.category, mainImage: project.image, album, description: project.description };
    data.projects.push(newProject);
    writeFallback(data);
    return newProject;
  },
  updateProject: async (id: number, project: { title: string; category: string; image: string; description: string; album?: string[] }): Promise<boolean> => {
    const album = project.album || [project.image];
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query('UPDATE projects SET title=?, category=?, image=?, description=?, album=? WHERE id=?', [project.title, project.category, project.image, project.description, JSON.stringify(album), id]);
        return (result.affectedRows ?? 0) > 0;
      } catch (err) { console.error('MySQL updateProject error:', err); }
    }
    const data = readFallback();
    const idx = data.projects.findIndex(p => p.id === id);
    if (idx !== -1) { data.projects[idx] = { ...data.projects[idx], title: project.title, category: project.category, mainImage: project.image, album, description: project.description }; writeFallback(data); return true; }
    return false;
  },
  deleteProject: async (id: number): Promise<boolean> => {
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query('DELETE FROM projects WHERE id=?', [id]);
        return (result.affectedRows ?? 0) > 0;
      } catch (err) { console.error('MySQL deleteProject error:', err); }
    }
    const data = readFallback();
    const before = data.projects.length;
    data.projects = data.projects.filter(p => p.id !== id);
    writeFallback(data);
    return data.projects.length < before;
  },
  getTimeline: async (): Promise<any[]> => {
    if (useMySQL && pool) {
      try {
        const [rows]: any = await pool.query('SELECT * FROM timeline ORDER BY year ASC, id ASC');
        return rows;
      } catch (err) { console.error('MySQL getTimeline error:', err); }
    }
    return [...readFallback().timeline].sort((a, b) => a.year.localeCompare(b.year));
  },
  addTimeline: async (item: { year: string; title: string; description: string; image: string }): Promise<any> => {
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query('INSERT INTO timeline (year, title, description, image) VALUES (?, ?, ?, ?)', [item.year, item.title, item.description, item.image]);
        return { id: result.insertId, ...item };
      } catch (err) { console.error('MySQL addTimeline error:', err); }
    }
    const data = readFallback();
    const newId = data.timeline.length > 0 ? Math.max(...data.timeline.map(t => t.id)) + 1 : 1;
    const newItem = { id: newId, ...item };
    data.timeline.push(newItem);
    writeFallback(data);
    return newItem;
  },
  updateTimeline: async (id: number, item: { year: string; title: string; description: string; image: string }): Promise<boolean> => {
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query('UPDATE timeline SET year=?, title=?, description=?, image=? WHERE id=?', [item.year, item.title, item.description, item.image, id]);
        return (result.affectedRows ?? 0) > 0;
      } catch (err) { console.error('MySQL updateTimeline error:', err); }
    }
    const data = readFallback();
    const idx = data.timeline.findIndex(t => t.id === id);
    if (idx !== -1) { data.timeline[idx] = { id, ...item }; writeFallback(data); return true; }
    return false;
  },
  deleteTimeline: async (id: number): Promise<boolean> => {
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query('DELETE FROM timeline WHERE id=?', [id]);
        return (result.affectedRows ?? 0) > 0;
      } catch (err) { console.error('MySQL deleteTimeline error:', err); }
    }
    const data = readFallback();
    const before = data.timeline.length;
    data.timeline = data.timeline.filter(t => t.id !== id);
    writeFallback(data);
    return data.timeline.length < before;
  },
  verifyUser: async (username: string, pass: string): Promise<any | null> => {
    const hashed = hashPassword(pass);
    if (useMySQL && pool) {
      try {
        const [rows]: any = await pool.query('SELECT * FROM users WHERE username=? AND password=?', [username, hashed]);
        if (rows.length > 0) return { id: rows[0].id, username: rows[0].username };
        return null;
      } catch (err) { console.error('MySQL verifyUser error:', err); }
    }
    const found = readFallback().users.find(u => u.username === username && u.password === hashed);
    return found ? { id: found.id, username: found.username } : null;
  },
  updateAdminUser: async (username: string, newPassword?: string): Promise<boolean> => {
    if (useMySQL && pool) {
      try {
        const [result]: any = await pool.query(
          newPassword ? 'UPDATE users SET username=?, password=? WHERE id=1' : 'UPDATE users SET username=? WHERE id=1',
          newPassword ? [username, hashPassword(newPassword)] : [username]
        );
        return (result.affectedRows ?? 0) > 0;
      } catch (err) { console.error('MySQL updateAdminUser error:', err); }
    }
    const data = readFallback();
    const admin = data.users.find(u => u.id === 1) || data.users[0];
    if (admin) { admin.username = username; if (newPassword) admin.password = hashPassword(newPassword); writeFallback(data); return true; }
    return false;
  },
  getSettings: async (): Promise<any> => {
    if (useMySQL && pool) {
      try {
        const [rows]: any = await pool.query('SELECT * FROM settings WHERE id=1');
        if (rows.length > 0) return { heroImage: rows[0].hero_image, aboutImage: rows[0].about_image };
      } catch (err) { console.error('MySQL getSettings error:', err); }
    }
    return readFallback().settings || { heroImage: '/images/banner-principal.jpg', aboutImage: '/images/sobre-nos.jpg' };
  },
  updateSettings: async (settings: { heroImage: string; aboutImage: string }): Promise<boolean> => {
    if (useMySQL && pool) {
      try {
        await pool.query('INSERT INTO settings (id, hero_image, about_image) VALUES (1, ?, ?) ON DUPLICATE KEY UPDATE hero_image=VALUES(hero_image), about_image=VALUES(about_image)', [settings.heroImage, settings.aboutImage]);
        return true;
      } catch (err) { console.error('MySQL updateSettings error:', err); }
    }
    const data = readFallback();
    data.settings = settings;
    writeFallback(data);
    return true;
  }
};
