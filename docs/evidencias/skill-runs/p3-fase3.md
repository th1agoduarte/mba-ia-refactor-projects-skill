# Projeto 3 — task-manager-api: Fase 3 (saída bruta do Claude Code)

Comando: `claude -p --resume 3b865ce0-f373-40e1-add1-908a4589aec8 "y"` (resposta à pergunta da Fase 2)
- Sessão: `3b865ce0-f373-40e1-add1-908a4589aec8`
- Turnos: 56 | duração: 493.4 s | custo estimado: US$ 3.84
- Tokens: entrada 58 (+cache 4186873), saída 55374
- Status: success | erro: False

---

The refactor is done. The app boots with the same `python seed.py && python app.py`, and all 47 baseline calls behave the same except 7 intentional changes: 4 now require an admin credential and 3 that used to crash with a 500 now return 400. Nothing is committed.

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
```
task-manager-api/
├── app.py                        # composition root: create_app() wires config, db, services, controllers, routes, error handlers; `python app.py`
├── seed.py                       # uses create_app(); same seed users and passwords, now stored with a strong hash
├── database.py                   # db = SQLAlchemy() + utcnow() helper (replaces datetime.utcnow)
├── requirements.txt              # flask, flask-sqlalchemy, flask-cors, python-dotenv (unused marshmallow/requests removed)
├── .env.example                  # every variable documented
├── config/settings.py            # env-based Settings + named domain constants (statuses, roles, limits, colors)
├── models/
│   ├── task.py                   # entity, is_overdue(), to_dict()/to_summary_dict(), aggregate queries (GROUP BY, joinedload)
│   ├── user.py                   # scrypt hash, to_dict() without password, cascade delete of tasks, task_count via join
│   └── category.py               # entity + task_count via join
├── controllers/
│   ├── task_controller.py        # task use cases (validation, transaction, notification)
│   ├── user_controller.py        # sign-up, update, delete, login (signed token)
│   ├── category_controller.py    # category CRUD (moved out of the reports module)
│   ├── report_controller.py      # summary and per-user report
│   ├── validators.py             # shared validations (raise ValidationError)
│   └── metrics.py                # completion_rate()
├── routes/                       # thin blueprints: extract input → controller → JSON + status
│   ├── task_routes.py · user_routes.py · category_routes.py · report_routes.py
│   └── system_routes.py          # GET / and GET /health
├── middlewares/
│   ├── error_handler.py          # domain exceptions + central handler ({"error": ...})
│   └── auth.py                   # authorize_admin / @require_admin (Bearer ADMIN_TOKEN or an admin's login token)
└── services/
    ├── notification_service.py   # SMTP from config; disabled without SMTP_HOST (log only)
    └── token_service.py          # signed tokens (itsdangerous, ships with Flask)
```
`utils/` was removed: all of it was dead code.

## Changes by Finding
- **F-01** → `SECRET_KEY` and SMTP settings now come from the environment. Without `SECRET_KEY`, a random key is generated with a warning in the log (T-01).
- **F-02** → `User.to_dict()` no longer includes `password` (T-04).
- **F-03** → `generate_password_hash`/`check_password_hash` (scrypt with salt). The seed stores the hash, so `joao/1234`, `maria/abcd`, `pedro/pass` still log in (T-04).
- **F-04** → `DELETE /users/<id>`, creating a user with `role != user`, and changing a user's `role` now require `Authorization: Bearer` with either `ADMIN_TOKEN` or the login token of an admin user. The predictable `fake-jwt-token-<id>` is replaced by a signed token (T-12).
- **F-05** → `create_app()` factory with dependencies injected into controllers. `seed.py` uses the factory, and importing `app` no longer has side effects (T-08, T-03).
- **F-06** → Debug off, `HOST=127.0.0.1` and CORS only for `CORS_ORIGINS` by default, all configurable (T-01).
- **F-07** → Report aggregations moved to `ReportController` plus query methods on the models (T-07).
- **F-08** → `TaskController` concentrates create/update/delete/search/stats, and the routes have 1–3 lines each (T-07).
- **F-09** → `UserController` concentrates sign-up, update, delete and login (T-07).
- **F-10** → `db.session.get()` and `select()` replace `Query.get`/`.query`, and `utcnow()` replaces `datetime.utcnow`. Zero warnings under `python -W default` (T-11).
- **F-11** → A single `Task.is_overdue()`, `to_dict(include_overdue, include_relations)`, `to_summary_dict()` and `completion_rate()` (T-14).
- **F-12** → `joinedload` on `/tasks`, `GROUP BY` for status, priority, per-user and per-category counts, and an outer join for `task_count` (T-06).
- **F-13** → Shared validators with constants. Wrong types and a `null` body now return 400, and colors, `active` and names are validated (T-13).
- **F-14** → `register_error_handlers` with `AppError`/`NotFoundError`/... in the `{"error": ...}` format. All 16 `except:` blocks are gone (T-05).
- **F-15** → Unused imports, dead methods, `utils/` and the unused dependencies removed. `NotificationService` is now wired into task assignment (T-14).
- **F-16** → Statuses, priorities, limits, color and the 7-day window are named constants in `config/settings.py` (T-13).
- **F-17** → Categories have their own module and blueprint; the opaque names (`p1`–`p5`, `d`, `cat`) are gone (T-14).
- **F-18** → Boolean expressions return directly (`return self.role == ROLE_ADMIN`, a one-line `is_overdue`) (T-13).
- **F-19** → `logging` is configured in the composition root, and the logs no longer include personal data (T-05).

## Contract Changes (security)
- `password` (the hash) was removed from the responses of `GET /users/<id>`, `POST /users`, `PUT /users/<id>` and `POST /login`.
- `DELETE /users/<id>` → 401 without a credential and 403 with a non-admin user's token. Auth is checked before the user lookup, so `DELETE /users/9999` without a token is now 401 instead of 404.
- `POST /users` with `role` other than `user` and `PUT /users/<id>` that changes `role` → 401/403 without an admin credential.
- The `token` from `POST /login` is now a signed token (same key, different value).
- Default runtime: CORS is off unless `CORS_ORIGINS` is set (it was `*`), and the server binds to `127.0.0.1` unless `HOST` is set (it was `0.0.0.0`). Set those variables to restore the old exposure.
- Robustness (not security, but listed so nothing is hidden), 500 → 400 with `{"error": ...}`:
  - `POST /tasks` with `priority` sent as a string;
  - `GET /tasks/search?priority=abc`;
  - `PUT /categories/<id>` with a `null` body.

## Validation
  ✓ Application boots without errors (`python seed.py && python app.py`, run with `-W default`: no tracebacks, no DeprecationWarning or LegacyAPIWarning)
  ✓ Endpoints respond correctly (40/47 calls match the baseline on status; the other 7 are exactly the changes listed above). All 22 routes were covered. Body comparison with timestamps masked: identical except the removed `password`, the protected operations, and the 500→400 cases. The summary differs only by user "X", whose creation was now blocked.
  ✓ Admin cases checked:
    - with `ADMIN_TOKEN`: create admin → 201, change role → 200, delete → 200; wrong token → 401;
    - with login tokens: maria (non-admin) → 403, joao (admin) → 200, and deleting a user also deleted that user's 3 tasks;
    - the old `fake-jwt-token-1` → 401.
  ✓ Zero anti-patterns remaining: pyflakes is clean and there are no `datetime.utcnow`, `.query.get`, `except:`, `debug=True` or `CORS(app)` left. The only remaining hits are justified:
    - the seed's demo passwords (they must stay the same so the seed users can still log in, and are stored hashed);
    - the `print` calls in `seed.py` (CLI output);
    - the project's own `utcnow()` helper.
================================

- **Database:** `instance/tasks.db` was regenerated with `python seed.py`. The old one had MD5 hashes that the new login can't check, and a backup is at `/tmp/task-manager-tasks.db.bak`.
- **Notifications:** task assignment now triggers a notification. Without `SMTP_HOST` it only writes a log line, so no email is sent by default.