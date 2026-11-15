const crypto = require('node:crypto');
const { promisify } = require('node:util');

const scrypt = promisify(crypto.scrypt);
const SALT_BYTES = 16;
const KEY_LENGTH = 64;

// Formato armazenado: scrypt$<salt hex>$<hash hex>
async function hashPassword(plain) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const key = await scrypt(plain, salt, KEY_LENGTH);
    return `scrypt$${salt}$${key.toString('hex')}`;
}

module.exports = { hashPassword };
