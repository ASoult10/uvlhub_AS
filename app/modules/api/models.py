from app import db
from datetime import datetime
import secrets

class ApiKey(db.Model):
    """Modelo para almacenar las API keys de los usuarios"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))  
    scopes = db.Column(db.String(255), default='read:datasets')  
    is_active = db.Column(db.Boolean, default=True)
    requests_count = db.Column(db.Integer, default=0)  
    last_used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  
    
    user = db.relationship('User', backref='api_keys')
    
    @staticmethod
    def generate_key():
        """Genera una API key aleatoria segura"""
        return secrets.token_urlsafe(32)
    
    def has_scope(self, required_scope):
        """Verifica si la key tiene un permiso específico"""
        if not self.scopes:
            return False
        user_scopes = [s.strip() for s in self.scopes.split(',')]
        return required_scope in user_scopes
    
    def increment_usage(self):
        """Incrementa el contador de uso"""
        self.requests_count += 1
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def is_valid(self):
        """Verifica si la key está activa y no ha expirado"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True