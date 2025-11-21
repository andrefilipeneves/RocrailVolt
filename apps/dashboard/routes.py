from flask import render_template, jsonify
from . import blueprint
from apps.authentication.models import Users
from ..models import ActivityLog

@blueprint.route('/')
def home():
    return render_template('dashboard.html')

@blueprint.route('/stats')
def stats():
    return jsonify({
        'total_users': Users.query.count(),
        'logs': ActivityLog.query.count()
    })
