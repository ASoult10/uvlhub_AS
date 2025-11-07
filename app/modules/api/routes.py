from flask import jsonify, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.modules.api import api_bp
from app.modules.api.services import require_api_key, limiter
from app.modules.api.models import ApiKey
from app.modules.api.forms import ApiKeyForm, RevokeApiKeyForm
from app.modules.dataset.models import DataSet, DSMetaData
from app import db
from datetime import datetime

# ==================== FRONTEND ROUTES ====================

@api_bp.route('/manage', methods=['GET'])
@login_required
def manage_keys():
    """Vista para gestionar las API keys del usuario"""
    form = ApiKeyForm()
    revoke_form = RevokeApiKeyForm()
    
    # Obtener las keys del usuario actual
    user_keys = ApiKey.query.filter_by(user_id=current_user.id).order_by(ApiKey.created_at.desc()).all()
    
    return render_template('api/manage_keys.html', 
                         form=form, 
                         revoke_form=revoke_form,
                         api_keys=user_keys)


@api_bp.route('/create', methods=['POST'])
@login_required
def create_key():
    """Crear una nueva API key"""
    form = ApiKeyForm()
    
    if form.validate_on_submit():
        # Generar la key
        new_key = ApiKey(
            key=ApiKey.generate_key(),
            user_id=current_user.id,
            name=form.name.data,
            scopes=','.join(form.scopes.data),
            expires_at=form.expires_at.data if form.expires_at.data else None
        )
        
        db.session.add(new_key)
        db.session.commit()
        
        flash(f'API Key created successfully! Key: {new_key.key}', 'success')
        flash('⚠️ Save this key now! You won\'t be able to see it again.', 'warning')
    else:
        flash('Error creating API key. Please check the form.', 'danger')
    
    return redirect(url_for('api.manage_keys'))


@api_bp.route('/revoke/<int:key_id>', methods=['POST'])
@login_required
def revoke_key(key_id):
    """Revocar una API key"""
    api_key = ApiKey.query.get_or_404(key_id)
    
    # Verificar que la key pertenece al usuario actual
    if api_key.user_id != current_user.id:
        flash('You do not have permission to revoke this key.', 'danger')
        return redirect(url_for('api.manage_keys'))
    
    api_key.is_active = False
    db.session.commit()
    
    flash(f'API Key "{api_key.name}" has been revoked.', 'info')
    return redirect(url_for('api.manage_keys'))


@api_bp.route('/delete/<int:key_id>', methods=['POST'])
@login_required
def delete_key(key_id):
    """Eliminar permanentemente una API key"""
    api_key = ApiKey.query.get_or_404(key_id)
    
    if api_key.user_id != current_user.id:
        flash('You do not have permission to delete this key.', 'danger')
        return redirect(url_for('api.manage_keys'))
    
    db.session.delete(api_key)
    db.session.commit()
    
    flash(f'API Key "{api_key.name}" has been deleted permanently.', 'success')
    return redirect(url_for('api.manage_keys'))


# ==================== API ENDPOINTS ====================

@api_bp.route('/datasets/<int:id>', methods=['GET'])
@limiter.limit("100 per hour")
@require_api_key(scope='read:datasets')
def get_dataset(api_key_obj, id):
    """
    GET /api/datasets/123
    Headers: X-API-Key: your_api_key_here
    """
    try:
        dataset = DataSet.query.get_or_404(id)
        metadata = DSMetaData.query.filter_by(data_set_id=id).first()
        
        return jsonify({
            'id': dataset.id,
            'title': metadata.title if metadata else None,
            'description': metadata.description if metadata else None,
            'created_at': dataset.created_at.isoformat() if dataset.created_at else None,
            'user_id': dataset.user_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api_bp.route('/search', methods=['GET'])
@limiter.limit("100 per hour")
@require_api_key(scope='read:datasets')
def search_datasets(api_key_obj):
    """
    GET /api/search?q=feature&page=1&per_page=10
    Headers: X-API-Key: your_api_key_here
    """
    try:
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        if not query:
            return jsonify({'error': 'Query parameter "q" is required'}), 400
        
        # Búsqueda
        datasets_query = DataSet.query.join(DSMetaData).filter(
            DSMetaData.title.ilike(f'%{query}%') |
            DSMetaData.description.ilike(f'%{query}%')
        )
        
        pagination = datasets_query.paginate(page=page, per_page=per_page, error_out=False)
        
        results = []
        for ds in pagination.items:
            metadata = DSMetaData.query.filter_by(data_set_id=ds.id).first()
            results.append({
                'id': ds.id,
                'title': metadata.title if metadata else None,
                'description': metadata.description if metadata else None,
                'created_at': ds.created_at.isoformat() if ds.created_at else None
            })
        
        return jsonify({
            'query': query,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/stats', methods=['GET'])
def api_stats():
    """Endpoint público sin autenticación"""
    return jsonify({
        'total_datasets': DataSet.query.count(),
        'version': '1.0'
    }), 200


@api_bp.route('/docs', methods=['GET'])
def api_documentation():
    """Documentación de la API"""
    return render_template('api/documentation.html')