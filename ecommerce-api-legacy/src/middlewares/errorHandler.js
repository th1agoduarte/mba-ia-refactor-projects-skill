const { AppError } = require('../errors');

// Encaminha rejeições de handlers async para o middleware de erro.
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

// Último middleware: converte erros de domínio em status HTTP e esconde detalhes de erros inesperados.
function createErrorHandler(logger) {
    // O Express só reconhece middleware de erro com 4 parâmetros.
    return (err, req, res, next) => {
        if (res.headersSent) return next(err);
        if (err instanceof AppError) return res.status(err.status).send(err.message);
        // Erros do express.json() (JSON malformado, corpo grande demais) já trazem status 4xx.
        if (err.expose && err.status >= 400 && err.status < 500) return res.status(err.status).send('Bad Request');

        logger.error(`Erro não tratado em ${req.method} ${req.path}`, err);
        return res.status(500).send('Erro interno');
    };
}

module.exports = { asyncHandler, createErrorHandler };
