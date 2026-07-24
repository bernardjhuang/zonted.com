// Minimal static server for local preview of zonted.com.
import http from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { join, extname } from 'node:path'

const ROOT = '/Users/bjh/Documents/zonted.com'
const PORT = 8099
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json',
  '.glb': 'model/gltf-binary',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.avif': 'image/avif',
  '.svg': 'image/svg+xml',
  '.xml': 'application/xml',
  '.txt': 'text/plain; charset=utf-8',
  '.ico': 'image/x-icon',
}

http
  .createServer(async (req, res) => {
    try {
      const path = decodeURIComponent((req.url || '/').split('?')[0])
      let fp = join(ROOT, path)
      const s = await stat(fp).catch(() => null)
      if (s && s.isDirectory()) fp = join(fp, 'index.html')
      const data = await readFile(fp)
      res.writeHead(200, { 'content-type': TYPES[extname(fp)] || 'application/octet-stream' })
      res.end(data)
    } catch {
      res.writeHead(404, { 'content-type': 'text/plain' })
      res.end('404 Not Found')
    }
  })
  .listen(PORT, () => console.log(`zonted-local on http://localhost:${PORT}`))
