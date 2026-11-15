const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

// Contrato público: os campos usr, eml, pwd, c_id e card são mantidos como no sistema legado.
function createCheckoutRoutes(checkoutController) {
    const router = express.Router();

    router.post('/api/checkout', asyncHandler(async (req, res) => {
        const body = req.body || {};
        const result = await checkoutController.checkout({
            name: body.usr,
            email: body.eml,
            password: body.pwd,
            courseId: body.c_id,
            cardNumber: body.card,
        });
        res.status(200).json(result);
    }));

    return router;
}

module.exports = { createCheckoutRoutes };
