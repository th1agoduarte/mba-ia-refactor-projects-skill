const { PAYMENT_STATUS } = require('../config/constants');

// Dados iniciais (os mesmos do sistema legado). A senha do usuário do seed é gravada com hash.
async function seedDatabase(db, models) {
    if (await models.users.count() > 0) return;

    await db.transaction(async () => {
        const userId = await models.users.create({ name: 'Leonan', email: 'leonan@fullcycle.com.br', password: '123' });
        const cleanArchId = await models.courses.create({ title: 'Clean Architecture', price: 997.00 });
        await models.courses.create({ title: 'Docker', price: 497.00 });
        const enrollmentId = await models.enrollments.create(userId, cleanArchId);
        await models.payments.create(enrollmentId, 997.00, PAYMENT_STATUS.PAID);
    });
}

module.exports = { seedDatabase };
