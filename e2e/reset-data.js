const fs = require('node:fs');
const path = require('node:path');

const dataDirectory = path.join(__dirname, '..', '.e2e-data');
fs.rmSync(dataDirectory, {recursive: true, force: true});
fs.mkdirSync(dataDirectory, {recursive: true});
