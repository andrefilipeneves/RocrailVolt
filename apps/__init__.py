# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module

# Initialize extensions

db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app):
    for module_name in ('authentication', 'home', 'dyn_dt', 'charts', 'api', 'dashboard', ):
        module = import_module(f'apps.{module_name}.routes')
        app.register_blueprint(module.blueprint)


def create_app(config):
    # Contextual configuration for templates and static folders
    static_prefix = '/static'
    # Determine base directory either from config or fallback to project root
    base_dir = getattr(config, 'BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    TEMPLATES_FOLDER = os.path.join(base_dir, 'templates')
    STATIC_FOLDER = os.path.join(base_dir, 'static')

    print(' > TEMPLATES_FOLDER: ' + TEMPLATES_FOLDER)
    print(' > STATIC_FOLDER:    ' + STATIC_FOLDER)

    app = Flask(__name__, static_url_path=static_prefix, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)
    app.config.from_object(config)

    # Register extensions and blueprints
    register_extensions(app)
    register_blueprints(app)

    # Register OAuth blueprints for authentication
    from apps.authentication.oauth import github_blueprint, google_blueprint
    app.register_blueprint(github_blueprint, url_prefix="/login")
    app.register_blueprint(google_blueprint, url_prefix="/login")

    return app
