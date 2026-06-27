const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const IMAGES_DIR = path.join(__dirname, '../venom-wordpress/preview/images');
const SUPPORTED = ['.jpg', '.jpeg', '.png'];

async function convertToWebP(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (!SUPPORTED.includes(ext)) return;

  const webpPath = filePath.replace(/\.(jpg|jpeg|png)$/i, '.webp');

  if (fs.existsSync(webpPath)) {
    const srcMtime = fs.statSync(filePath).mtimeMs;
    const dstMtime = fs.statSync(webpPath).mtimeMs;
    if (dstMtime >= srcMtime) return; // already up to date
  }

  await sharp(filePath)
    .webp({ quality: 85 })
    .toFile(webpPath);

  const srcSize = fs.statSync(filePath).size;
  const dstSize = fs.statSync(webpPath).size;
  const saved = (((srcSize - dstSize) / srcSize) * 100).toFixed(1);
  console.log(`✓ ${path.basename(filePath)} → ${path.basename(webpPath)} (${saved}% smaller)`);
}

async function run() {
  if (!fs.existsSync(IMAGES_DIR)) {
    console.log('Images directory not found:', IMAGES_DIR);
    return;
  }

  const files = fs.readdirSync(IMAGES_DIR)
    .filter(f => SUPPORTED.includes(path.extname(f).toLowerCase()))
    .map(f => path.join(IMAGES_DIR, f));

  if (files.length === 0) {
    console.log('No images to convert.');
    return;
  }

  console.log(`Converting ${files.length} image(s) to WebP...`);
  await Promise.all(files.map(convertToWebP));
  console.log('Done.');
}

run().catch(console.error);
