// Exceções de domínio: o middleware de erro converte `status` em código HTTP.
class AppError extends Error {
    constructor(message, status = 400) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class PaymentDeniedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autorizado') { super(message, 401); }
}

class ForbiddenError extends AppError {
    constructor(message = 'Acesso negado') { super(message, 403); }
}

class NotFoundError extends AppError {
    constructor(message = 'Não encontrado') { super(message, 404); }
}

module.exports = { AppError, ValidationError, PaymentDeniedError, UnauthorizedError, ForbiddenError, NotFoundError };
