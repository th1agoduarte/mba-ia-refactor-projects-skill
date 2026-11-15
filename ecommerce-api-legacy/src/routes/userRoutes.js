const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

function createUserRoutes(userController, requireAdmin) {
    const router = express.Router();

    router.delete('/api/users/:id', requireAdmin, asyncHandler(async (req, res) => {
        await userController.delete(req.params.id);
        res.send('Usuário deletado, junto com suas matrículas e pagamentos.');
    }));

    return router;
}

module.exports = { createUserRoutes };
