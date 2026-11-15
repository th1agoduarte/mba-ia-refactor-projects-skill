const { PAYMENT_STATUS, UNKNOWN_STUDENT } = require('../config/constants');

class ReportController {
    constructor({ reports }) {
        this.reports = reports;
    }

    // Receita por curso (só pagamentos PAID) e lista de alunos com o valor pago.
    async financialReport() {
        const rows = await this.reports.financialRows();
        const byCourse = new Map();

        for (const row of rows) {
            if (!byCourse.has(row.course_id)) {
                byCourse.set(row.course_id, { course: row.course, revenue: 0, students: [] });
            }
            if (row.enrollment_id === null) continue;

            const entry = byCourse.get(row.course_id);
            if (row.status === PAYMENT_STATUS.PAID) entry.revenue += row.amount;
            entry.students.push({ student: row.student ?? UNKNOWN_STUDENT, paid: row.amount ?? 0 });
        }

        return [...byCourse.values()];
    }
}

module.exports = ReportController;
