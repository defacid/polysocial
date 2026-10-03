const fs = require('node:fs');
const path = require('node:path');

module.exports = async () => {
  fs.rmSync(path.join(__dirname, '..', '.e2e-data'), {recursive: true, force: true});
};
