from flask import render_template, jsonify
from . import blueprint
from ..models import User, ActivityLog

@blueprint.route('/')
def home():
    return render_template('dashboard.html')

@blueprint.route('/stats')
def stats():
    return jsonify({
        'total_users': User.query.count(),
        'logs': ActivityLog.query.count()
    })
