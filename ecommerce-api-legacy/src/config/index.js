const fs = require('node:fs');
const path = require('node:path');

// Opcional: carrega ./.env da raiz do projeto. Variáveis já definidas no ambiente têm precedência.
const ENV_FILE = path.resolve(__dirname, '../../.env');
if (fs.existsSync(ENV_FILE)) process.loadEnvFile(ENV_FILE);

const DEFAULT_PORT = 3000;

module.exports = Object.freeze({
    port: Number(process.env.PORT) || DEFAULT_PORT,
    dbPath: process.env.DB_PATH || ':memory:',
    // Vazio = gateway simulado (nenhuma chave no código).
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    // Vazio = endpoints administrativos desabilitados (403).
    adminToken: process.env.ADMIN_TOKEN || '',
    logLevel: process.env.LOG_LEVEL || 'info',
});
