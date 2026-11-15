const { hashPassword } = require('./password');

class UserModel {
    constructor(db) {
        this.db = db;
    }

    findByEmail(email) {
        return this.db.get('SELECT id, name, email FROM users WHERE email = ?', [email]);
    }

    // Sem senha informada, a conta fica sem credencial (pass NULL), em vez de receber uma senha padrão.
    async create({ name, email, password }) {
        const passwordHash = password ? await hashPassword(password) : null;
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, passwordHash],
        );
        return lastID;
    }

    async deleteById(id) {
        const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
        return changes > 0;
    }

    async count() {
        const row = await this.db.get('SELECT COUNT(*) AS total FROM users');
        return row.total;
    }
}

module.exports = UserModel;
