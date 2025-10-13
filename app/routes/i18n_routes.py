from flask import Blueprint, request, jsonify, session

i18n_bp = Blueprint('i18n', __name__)

@i18n_bp.route('/set', methods=['POST'])
def set_locale():
    data = request.get_json(silent=True) or {}
    lang = (data.get('lang') or request.args.get('lang') or 'en').lower()
    if lang not in ['en', 'fr', 'de', 'hi', 'gu']:
        return jsonify({'error': 'Unsupported language'}), 400
    session['lang'] = lang
    return jsonify({'message': 'Language updated', 'lang': lang})
