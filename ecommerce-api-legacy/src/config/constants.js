const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Regra do gateway simulado: cartões iniciados com este prefixo são aprovados.
const SIMULATED_APPROVED_CARD_PREFIX = '4';

const COURSE_ACTIVE = 1;

// Nome exibido no relatório quando a matrícula aponta para um usuário inexistente.
const UNKNOWN_STUDENT = 'Unknown';

module.exports = { PAYMENT_STATUS, SIMULATED_APPROVED_CARD_PREFIX, COURSE_ACTIVE, UNKNOWN_STUDENT };
