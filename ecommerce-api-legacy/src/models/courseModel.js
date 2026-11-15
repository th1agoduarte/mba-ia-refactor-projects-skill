const { COURSE_ACTIVE } = require('../config/constants');

class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(id) {
        return this.db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = ?', [id, COURSE_ACTIVE]);
    }

    async create({ title, price, active = COURSE_ACTIVE }) {
        const { lastID } = await this.db.run(
            'INSERT INTO courses (title, price, active) VALUES (?, ?, ?)',
            [title, price, active],
        );
        return lastID;
    }
}

module.exports = CourseModel;
