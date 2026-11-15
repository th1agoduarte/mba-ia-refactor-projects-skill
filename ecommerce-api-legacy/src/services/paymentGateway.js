const { PAYMENT_STATUS, SIMULATED_APPROVED_CARD_PREFIX } = require('../config/constants');

const VISIBLE_CARD_DIGITS = 4;

// Gateway simulado atrás de uma interface `charge`. Um gateway real implementaria o mesmo método
// usando `apiKey` (vinda da config, nunca do código).
class SimulatedPaymentGateway {
    constructor({ apiKey, logger }) {
        this.apiKey = apiKey;
        this.logger = logger;
    }

    async charge({ cardNumber, amount }) {
        const status = cardNumber.startsWith(SIMULATED_APPROVED_CARD_PREFIX)
            ? PAYMENT_STATUS.PAID
            : PAYMENT_STATUS.DENIED;
        this.logger.info(`Cobrança simulada: cartão final ${cardNumber.slice(-VISIBLE_CARD_DIGITS)}, valor ${amount}, status ${status}`);
        return status;
    }

    // Estorno de uma cobrança aprovada (usado quando a gravação do checkout falha depois da cobrança).
    async refund({ cardNumber, amount }) {
        this.logger.warn(`Estorno simulado: cartão final ${cardNumber.slice(-VISIBLE_CARD_DIGITS)}, valor ${amount}`);
    }
}

module.exports = { SimulatedPaymentGateway };
