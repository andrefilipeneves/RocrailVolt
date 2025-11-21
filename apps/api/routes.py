from flask import jsonify
from . import blueprint
from ..models import User, ActivityLog

@blueprint.route('/users')
def list_users():
    users = User.query.all()
    return jsonify([
        {'id': u.id, 'email': u.email, 'created_at': u.created_at.isoformat()} for u in users
    ])

@blueprint.route('/activity')
def activity():
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    return jsonify([
        {'event': l.event, 'created_at': l.created_at.isoformat()} for l in logs
    ])
