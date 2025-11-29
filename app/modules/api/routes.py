from flask import jsonify, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.modules.api import api_bp
from app.modules.api.services import require_api_key, limiter
from app.modules.api.models import ApiKey
from app.modules.api.forms import ApiKeyForm, RevokeApiKeyForm
from app.modules.dataset.models import DataSet, DSMetaData
from app import db
from datetime import datetime


@api_bp.route('/manage', methods=['GET'])
@login_required
def manage_keys():
    """Vista para gestionar las API keys del usuario"""
    form = ApiKeyForm()
    revoke_form = RevokeApiKeyForm()
    
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




@api_bp.route('/datasets/id/<int:id>', methods=['GET'])
@limiter.limit("100 per hour")
@require_api_key(scope='read:datasets')
def get_dataset_by_id(api_key_obj, id):
    """
    GET /api/datasets/id/123
    Headers: X-API-Key: your_api_key_here
    """
    try:
        dataset = DataSet.query.get(id)
        
        if not dataset:
            return jsonify({
                'error': 'not_found',
                'message': f'Dataset with id {id} not found'
            }), 404
        
        metadata = DSMetaData.query.get(dataset.ds_meta_data_id) if dataset.ds_meta_data_id else None
        
        return jsonify({
            'id': dataset.id,
            'title': metadata.title if metadata else None,
            'description': metadata.description if metadata else None,
            'publication_type': metadata.publication_type.value if metadata and metadata.publication_type else None,
            'tags': metadata.tags if metadata else None,
            'created_at': dataset.created_at.isoformat() if dataset.created_at else None,
            'user_id': dataset.user_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500




@api_bp.route('/datasets/title/<string:title>', methods=['GET'])
@limiter.limit("100 per hour")
@require_api_key(scope='read:datasets')
def get_dataset_by_title(api_key_obj, title):
    """
    GET /api/datasets/title/My-Dataset-Title
    Headers: X-API-Key: your_api_key_here
    """
    try:
        search_title = title.replace('-', ' ')
        metadata = DSMetaData.query.filter(
            DSMetaData.title.ilike(f'%{search_title}%')
        ).first()
        
        if not metadata:
            return jsonify({
                'error': 'not_found',
                'message': f'No dataset found with title containing "{search_title}"'
            }), 404
        
        dataset = DataSet.query.filter_by(ds_meta_data_id=metadata.id).first()
        
        if not dataset:
            return jsonify({
                'error': 'not_found',
                'message': 'Dataset metadata found but dataset record is missing'
            }), 404
        
        return jsonify({
            'id': dataset.id,
            'title': metadata.title,
            'description': metadata.description,
            'publication_type': metadata.publication_type.value if metadata.publication_type else None,
            'tags': metadata.tags,
            'created_at': dataset.created_at.isoformat() if dataset.created_at else None,
            'user_id': dataset.user_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'internal_error',
            'message': str(e)
        }), 500


@api_bp.route('/datasets', methods=['GET'])
@limiter.limit("100 per hour")
@require_api_key(scope='read:datasets')
def list_datasets(api_key_obj):
    """
    GET /api/datasets
    Headers: X-API-Key: your_api_key_here
    
    Devuelve TODOS los datasets sin paginación
    """
    try:
        datasets = DataSet.query.all()
        
        results = []
        for dataset in datasets:
            metadata = DSMetaData.query.get(dataset.ds_meta_data_id) if dataset.ds_meta_data_id else None
            
            results.append({
                'id': dataset.id,
                'title': metadata.title if metadata else None,
                'description': metadata.description if metadata else None,
                'publication_type': metadata.publication_type.value if metadata and metadata.publication_type else None,
                'tags': metadata.tags if metadata else None,
                'created_at': dataset.created_at.isoformat() if dataset.created_at else None,
                'user_id': dataset.user_id
            })
        
        return jsonify({
            'total': len(results),
            'datasets': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'internal_error',
            'message': str(e)
        }), 500



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
      
        metadata_results = DSMetaData.query.filter(
            DSMetaData.title.ilike(f'%{query}%') |
            DSMetaData.description.ilike(f'%{query}%')
        ).all()
        
        metadata_ids = [m.id for m in metadata_results]
        
        if not metadata_ids:
            return jsonify({
                'query': query,
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'results': []
            }), 200
        
        datasets_query = DataSet.query.filter(DataSet.ds_meta_data_id.in_(metadata_ids))
        pagination = datasets_query.paginate(page=page, per_page=per_page, error_out=False)
        
        results = []
        for ds in pagination.items:
            metadata = DSMetaData.query.get(ds.ds_meta_data_id)
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
@limiter.limit("100 per hour")
@require_api_key(scope='read:stats')
def api_stats(api_key_obj):
    """Stats protegidas por API Key (scope: read:stats)"""
    return jsonify({
        'total_datasets': DataSet.query.count(),
        'version': '1.0'
    }), 200


@api_bp.route('/docs', methods=['GET'])
def api_documentation():
    """Documentación de la API"""
    return render_template('api/documentation.html')