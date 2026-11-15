const sqlite3 = require('sqlite3');

// Abre o banco e expõe helpers que retornam Promise, mais uma transação serializada.
function openDatabase(dbPath) {
    return new Promise((resolve, reject) => {
        const raw = new sqlite3.Database(dbPath, (openErr) => {
            if (openErr) return reject(openErr);
            const db = wrap(raw);
            db.exec('PRAGMA foreign_keys = ON').then(() => resolve(db), reject);
        });
    });
}

function wrap(raw) {
    const run = (sql, params = []) => new Promise((resolve, reject) => {
        raw.run(sql, params, function onRun(err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
    const get = (sql, params = []) => new Promise((resolve, reject) => {
        raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    });
    const all = (sql, params = []) => new Promise((resolve, reject) => {
        raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    });
    const exec = (sql) => new Promise((resolve, reject) => {
        raw.exec(sql, (err) => (err ? reject(err) : resolve()));
    });
    const close = () => new Promise((resolve, reject) => {
        raw.close((err) => (err ? reject(err) : resolve()));
    });

    // A conexão é única: as transações entram numa fila para não se intercalarem.
    let queue = Promise.resolve();
    function transaction(work) {
        const result = queue.then(async () => {
            await run('BEGIN IMMEDIATE');
            try {
                const value = await work();
                await run('COMMIT');
                return value;
            } catch (err) {
                await run('ROLLBACK');
                throw err;
            }
        });
        queue = result.catch(() => {});
        return result;
    }

    return { run, get, all, exec, close, transaction };
}

module.exports = { openDatabase };
