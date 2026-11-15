const LEVELS = Object.freeze({ error: 0, warn: 1, info: 2, debug: 3 });

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;

    const writer = (name, stream) => (message, err) => {
        if (LEVELS[name] > threshold) return;
        const stack = err && err.stack ? `\n${err.stack}` : '';
        stream.write(`${new Date().toISOString()} ${name.toUpperCase()} ${message}${stack}\n`);
    };

    return {
        error: writer('error', process.stderr),
        warn: writer('warn', process.stderr),
        info: writer('info', process.stdout),
        debug: writer('debug', process.stdout),
    };
}

module.exports = { createLogger };
