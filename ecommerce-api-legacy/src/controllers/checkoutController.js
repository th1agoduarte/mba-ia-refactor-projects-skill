const { PAYMENT_STATUS } = require('../config/constants');
const { ValidationError, NotFoundError, PaymentDeniedError } = require('../errors');

const CARD_PATTERN = /^\d+$/;

function parseCourseId(value) {
    const id = Number(value);
    return Number.isInteger(id) && id > 0 ? id : null;
}

// Mantém a regra de presença do contrato original e rejeita cartão que não seja texto com dígitos.
function validateCheckout({ name, email, password, courseId, cardNumber }) {
    if (!name || !email || !courseId || !cardNumber) throw new ValidationError();
    if (typeof cardNumber !== 'string') throw new ValidationError();

    const normalizedCard = cardNumber.replace(/[\s-]/g, '');
    if (!CARD_PATTERN.test(normalizedCard)) throw new PaymentDeniedError();

    return {
        name: String(name),
        email: String(email),
        password: password ? String(password) : null,
        courseId: parseCourseId(courseId),
        cardNumber: normalizedCard,
    };
}

class CheckoutController {
    constructor({ db, courses, users, enrollments, payments, auditLogs, paymentGateway, logger }) {
        Object.assign(this, { db, courses, users, enrollments, payments, auditLogs, paymentGateway, logger });
    }

    async checkout(input) {
        const data = validateCheckout(input);

        const course = data.courseId && await this.courses.findActiveById(data.courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        const status = await this.paymentGateway.charge({ cardNumber: data.cardNumber, amount: course.price });
        if (status === PAYMENT_STATUS.DENIED) throw new PaymentDeniedError();

        const enrollmentId = await this.db.transaction(async () => {
            const existing = await this.users.findByEmail(data.email);
            const userId = existing
                ? existing.id
                : await this.users.create({ name: data.name, email: data.email, password: data.password });

            const newEnrollmentId = await this.enrollments.create(userId, course.id);
            await this.payments.create(newEnrollmentId, course.price, status);
            await this.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);
            return newEnrollmentId;
        });

        this.logger.info(`Checkout concluído: curso ${course.id}, matrícula ${enrollmentId}`);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }
}

module.exports = CheckoutController;
