from flask import jsonify
from . import blueprint
from apps.authentication.models import Users
from ..models import ActivityLog

@blueprint.route('/users')
def list_users():
    users = Users.query.all()
    return jsonify([
        {'id': u.id, 'username': u.username, 'email': u.email} for u in users
    ])

@blueprint.route('/activity')
def activity():
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    return jsonify([
        {'event': l.event, 'created_at': l.created_at.isoformat()} for l in logs
    ])
