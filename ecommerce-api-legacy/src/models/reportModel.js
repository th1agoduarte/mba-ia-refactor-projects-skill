// Leitura agregada para o relatório financeiro: uma única consulta em vez de 1 + C + 2·E.
class ReportModel {
    constructor(db) {
        this.db = db;
    }

    // Uma linha por matrícula (ou uma linha com enrollment_id NULL para curso sem matrículas).
    // Como no sistema legado, considera o primeiro pagamento de cada matrícula.
    financialRows() {
        return this.db.all(`
            SELECT c.id AS course_id, c.title AS course, e.id AS enrollment_id,
                   u.name AS student, p.amount AS amount, p.status AS status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u ON u.id = e.user_id
            LEFT JOIN payments p ON p.id = (
                SELECT MIN(id) FROM payments WHERE enrollment_id = e.id
            )
            ORDER BY c.id, e.id
        `);
    }
}

module.exports = ReportModel;
