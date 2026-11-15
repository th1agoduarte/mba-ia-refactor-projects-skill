class UserController {
    constructor({ db, users, enrollments, payments, logger }) {
        Object.assign(this, { db, users, enrollments, payments, logger });
    }

    // Remove o usuário com suas matrículas e pagamentos numa transação (sem registros órfãos).
    // Como no contrato original, um id inexistente ou inválido não é erro.
    async delete(rawId) {
        const userId = Number(rawId);
        if (!Number.isInteger(userId) || userId <= 0) return false;

        const deleted = await this.db.transaction(async () => {
            await this.payments.deleteByUserId(userId);
            await this.enrollments.deleteByUserId(userId);
            return this.users.deleteById(userId);
        });

        if (deleted) this.logger.info(`Usuário ${userId} removido com matrículas e pagamentos`);
        return deleted;
    }
}

module.exports = UserController;
