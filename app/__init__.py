from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from app.config import Config
from flask_babel import Babel
from flask import session, request

db = SQLAlchemy()
migrate = Migrate()
babel = Babel()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=app.config['FRONTEND_ORIGIN'], supports_credentials=True)

    # Babel i18n
    app.config.setdefault('BABEL_DEFAULT_LOCALE', 'en')
    app.config.setdefault('BABEL_SUPPORTED_LOCALES', ['en', 'fr', 'de', 'hi', 'gu'])
    babel.init_app(app)

    @babel.localeselector
    def get_locale():
        lang = session.get('lang')
        if lang:
            return lang
        return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])
    
    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.company_routes import company_bp
    from app.routes.expense_routes import expense_bp
    from app.routes.approval_routes import approval_bp
    from app.routes.notification_routes import notification_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.main_routes import main_bp
    from app.routes.utils_routes import utils_bp
    from app.routes.i18n_routes import i18n_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(company_bp, url_prefix='/api/company')
    app.register_blueprint(expense_bp, url_prefix='/api/expenses')
    app.register_blueprint(approval_bp, url_prefix='/api/approvals')
    app.register_blueprint(notification_bp, url_prefix='/api/notifications')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(utils_bp, url_prefix='/api/utils')
    app.register_blueprint(i18n_bp, url_prefix='/i18n')
    app.register_blueprint(main_bp)  # For rendered pages
    
    return app
