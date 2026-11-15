const crypto = require('node:crypto');
const { UnauthorizedError, ForbiddenError } = require('../errors');

const ADMIN_TOKEN_HEADER = 'X-Admin-Token';

function tokensMatch(received, expected) {
    const receivedBytes = Buffer.from(received);
    const expectedBytes = Buffer.from(expected);
    return receivedBytes.length === expectedBytes.length && crypto.timingSafeEqual(receivedBytes, expectedBytes);
}

// Exige o header X-Admin-Token igual a ADMIN_TOKEN. Sem ADMIN_TOKEN configurado, o recurso fica desabilitado.
function createAdminAuth(adminToken) {
    return (req, res, next) => {
        if (!adminToken) return next(new ForbiddenError('Endpoint administrativo desabilitado (defina ADMIN_TOKEN)'));
        if (!tokensMatch(req.get(ADMIN_TOKEN_HEADER) || '', adminToken)) return next(new UnauthorizedError());
        return next();
    };
}

module.exports = { createAdminAuth, ADMIN_TOKEN_HEADER };
