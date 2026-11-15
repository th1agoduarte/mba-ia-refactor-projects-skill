// Composition root: carrega a config, cria o banco, models, serviços e controllers, registra rotas e o
// middleware de erro. Executado diretamente (`npm start` → `node src/app.js`), sobe o servidor HTTP.
const express = require('express');
const config = require('./config');
const { createLogger } = require('./config/logger');
const { openDatabase } = require('./database/connection');
const { initSchema } = require('./database/schema');
const { seedDatabase } = require('./database/seed');
const UserModel = require('./models/userModel');
const CourseModel = require('./models/courseModel');
const EnrollmentModel = require('./models/enrollmentModel');
const PaymentModel = require('./models/paymentModel');
const AuditLogModel = require('./models/auditLogModel');
const ReportModel = require('./models/reportModel');
const { SimulatedPaymentGateway } = require('./services/paymentGateway');
const CheckoutController = require('./controllers/checkoutController');
const ReportController = require('./controllers/reportController');
const UserController = require('./controllers/userController');
const { createAdminAuth } = require('./middlewares/adminAuth');
const { createErrorHandler } = require('./middlewares/errorHandler');
const { createCheckoutRoutes } = require('./routes/checkoutRoutes');
const { createReportRoutes } = require('./routes/reportRoutes');
const { createUserRoutes } = require('./routes/userRoutes');

async function createApp({ settings = config, logger = createLogger(settings.logLevel) } = {}) {
    const db = await openDatabase(settings.dbPath);
    await initSchema(db);

    const models = {
        users: new UserModel(db),
        courses: new CourseModel(db),
        enrollments: new EnrollmentModel(db),
        payments: new PaymentModel(db),
        auditLogs: new AuditLogModel(db),
        reports: new ReportModel(db),
    };
    await seedDatabase(db, models);

    const paymentGateway = new SimulatedPaymentGateway({ apiKey: settings.paymentGatewayKey, logger });
    const checkoutController = new CheckoutController({ db, ...models, paymentGateway, logger });
    const reportController = new ReportController(models);
    const userController = new UserController({ db, ...models, logger });
    const requireAdmin = createAdminAuth(settings.adminToken);

    const app = express();
    app.use(express.json());
    app.use(createCheckoutRoutes(checkoutController));
    app.use(createReportRoutes(reportController, requireAdmin));
    app.use(createUserRoutes(userController, requireAdmin));
    app.use(createErrorHandler(logger));

    return { app, db };
}

async function main() {
    const logger = createLogger(config.logLevel);
    if (!config.adminToken) logger.warn('ADMIN_TOKEN não definido: endpoints administrativos respondem 403');
    if (!config.paymentGatewayKey) logger.warn('PAYMENT_GATEWAY_KEY não definida: usando gateway de pagamento simulado');

    const { app } = await createApp({ settings: config, logger });
    app.listen(config.port, () => logger.info(`LMS API rodando na porta ${config.port}`));
}

if (require.main === module) {
    main().catch((err) => {
        process.stderr.write(`Falha ao iniciar a aplicação: ${err.stack || err}\n`);
        process.exit(1);
    });
}

module.exports = { createApp };
