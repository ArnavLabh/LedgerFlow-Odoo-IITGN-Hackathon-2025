from flask import Blueprint, request, jsonify
from app import db
from app.models import Notification
from app.auth import token_required

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('', methods=['GET'])
@token_required
def get_notifications(current_user):
    """Get notifications for current user"""
    # Get limit from query params
    limit = request.args.get('limit', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if unread_only:
        query = query.filter_by(read=False)
    
    notifications = query.order_by(
        Notification.read.asc(),  # Unread first
        Notification.created_at.desc()
    ).limit(limit).all()
    
    # Get unread count
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).count()
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count
    })

@notification_bp.route('/mark-read', methods=['POST'])
@token_required
def mark_notifications_read(current_user):
    """Mark notifications as read"""
    data = request.get_json()
    notification_ids = data.get('notification_ids', [])
    
    if not notification_ids:
        # Mark all as read
        Notification.query.filter_by(
            user_id=current_user.id,
            read=False
        ).update({'read': True})
    else:
        # Mark specific notifications as read
        Notification.query.filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == current_user.id
        ).update({'read': True}, synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({'message': 'Notifications marked as read'})

@notification_bp.route('/count', methods=['GET'])
@token_required
def get_unread_count(current_user):
    """Get unread notification count"""
    count = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).count()
    
    return jsonify({'unread_count': count})