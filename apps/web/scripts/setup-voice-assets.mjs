/**
 * Downloads the Piper voice used for spoken answers into public/models/:
 * navgurukul-ai/Indian_accent_60, verified against known sha256 hashes.
 *
 * Idempotent and never fails `npm install`: if it can't download (e.g.
 * offline) it says so, and voice output stays unavailable until
 * `npm run voice:setup` succeeds. NEURALSHELF_SKIP_VOICE_ASSETS=1 skips it.
 */
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
const publicDir = path.join(root, 'public')
const log = (message) => console.log(`[voice-assets] ${message}`)

const MODEL_REPO = 'https://huggingface.co/navgurukul-ai/Indian_accent_60/resolve/main'
const MODEL_FILES = [
  {
    target: 'models/indian-accent-60.onnx',
    url: `${MODEL_REPO}/model.onnx`,
    sha256: '5fa27435a7759c77a9b10c1ef7ce6a0bb14e3f10c1c1b2d2ee9c008a673a6ca7',
  },
  {
    target: 'models/indian-accent-60.json',
    url: `${MODEL_REPO}/model.json`,
    sha256: 'fc1c99f3a7f2aa00e1986de5ab3203787007aa6e63bef406674d605448f9e1a6',
  },
]

function sha256(file) {
  return createHash('sha256').update(readFileSync(file)).digest('hex')
}

async function ensureModel({ target, url, sha256: expected }) {
  const file = path.join(publicDir, target)
  if (existsSync(file) && sha256(file) === expected) return true

  log(`downloading ${target} ...`)
  const response = await fetch(url)
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`)
  const data = Buffer.from(await response.arrayBuffer())
  const actual = createHash('sha256').update(data).digest('hex')
  if (actual !== expected) throw new Error(`${target}: checksum mismatch (got ${actual})`)
  mkdirSync(path.dirname(file), { recursive: true })
  writeFileSync(file, data)
  log(`downloaded ${target} (${(data.length / 1e6).toFixed(1)} MB, checksum ok)`)
  return true
}

async function main() {
  if (process.env.NEURALSHELF_SKIP_VOICE_ASSETS === '1')
    return log('skipped (NEURALSHELF_SKIP_VOICE_ASSETS=1)')

  for (const model of MODEL_FILES) {
    try {
      await ensureModel(model)
    } catch (error) {
      log(
        `could not fetch ${model.target}: ${error.message}. Voice output stays off until "npm run voice:setup" succeeds.`,
      )
    }
  }
}

main().catch((error) => log(`failed: ${error.message}`))
