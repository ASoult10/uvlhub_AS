from datetime import datetime

import geoip2.database
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
from user_agents import parse

from app.modules.token.models import Token, TokenType
from app.modules.token.repositories import TokenRepository
from core.services.BaseService import BaseService


class TokenService(BaseService):

    def __init__(self):
        repository = TokenRepository()
        super().__init__(repository)
        self.repository = repository

    def get_token_by_id(self, token_id):
        return self.repository.get_token_by_id(token_id)

    def get_token_by_jti(self, jti):
        return self.repository.get_token_by_jti(jti)

    def get_pair_of_tokens_by_jti(self, jti):
        access_token = self.repository.get_token_by_jti(jti)
        refresh_token = self.repository.get_token_by_jti(access_token.parent_jti) if access_token else None
        return access_token, refresh_token

    def get_active_tokens_by_user(self, user_id):
        return self.repository.get_active_tokens_by_user(user_id)

    def get_all_tokens_by_user(self, user_id):
        return self.repository.get_all_tokens_by_user(user_id)

    def revoke_token(self, token_id, user_id):
        token_to_revoke = self.get_token_by_id(token_id)
        parent_jti = token_to_revoke.parent_jti if token_to_revoke else None
        parent_token = self.get_token_by_jti(parent_jti) if parent_jti else None
        if token_to_revoke and token_to_revoke.user_id == user_id:
            self.edit_token(token_id, is_active=False)
            if parent_token and parent_token.user_id == user_id:
                self.edit_token(parent_token.id, is_active=False)
            return True
        return False

    def revoke_all_tokens_for_user(self, user_id):
        tokens_to_revoke = self.get_all_tokens_by_user(user_id)
        for token in tokens_to_revoke:
            self.edit_token(token.id, is_active=False)
        return len(tokens_to_revoke)

    def create_tokens(self, user_id, device_info, location_info):
        access_token = create_access_token(identity=str(user_id))
        refresh_token = create_refresh_token(identity=str(user_id))

        decoded_refresh = decode_token(refresh_token)
        refresh_jti = decoded_refresh.get("jti")
        exp_ts_refresh = decoded_refresh.get("exp")
        expires_at_refresh = datetime.utcfromtimestamp(exp_ts_refresh)

        refresh_token_data = {
            "user_id": user_id,
            "code": refresh_token,
            "type": TokenType.REFRESH_TOKEN,
            "is_active": True,
            "expires_at": expires_at_refresh,
            "device_info": device_info,
            "location_info": location_info,
            "jti": refresh_jti,
        }

        decoded_access = decode_token(access_token)
        access_jti = decoded_access.get("jti")
        exp_ts_access = decoded_access.get("exp")
        expires_at_access = datetime.utcfromtimestamp(exp_ts_access)

        access_token_data = {
            "user_id": user_id,
            "parent_jti": refresh_jti,
            "code": access_token,
            "type": TokenType.ACCESS_TOKEN,
            "is_active": True,
            "expires_at": expires_at_access,
            "device_info": device_info,
            "location_info": location_info,
            "jti": access_jti,
        }

        self.save_token(**refresh_token_data)
        self.save_token(**access_token_data)

        return access_token, refresh_token

    def refresh_access_token(self, user_id, device_info, location_info, parent_jti):
        old_access = self.repository.get_active_access_token_by_parent_jti(parent_jti)
        if old_access:
            self.edit_token(old_access.id, is_active=False)

        access_token = create_access_token(identity=str(user_id))

        decoded_access = decode_token(access_token)
        access_jti = decoded_access.get("jti")
        exp_ts_access = decoded_access.get("exp")
        expires_at_access = datetime.utcfromtimestamp(exp_ts_access)

        access_token_data = {
            "user_id": user_id,
            "parent_jti": parent_jti,
            "code": access_token,
            "type": TokenType.ACCESS_TOKEN,
            "is_active": True,
            "expires_at": expires_at_access,
            "device_info": device_info,
            "location_info": location_info,
            "jti": access_jti,
        }

        self.save_token(**access_token_data)

        return access_token

    def save_token(self, **kwargs):
        new_token = Token(**kwargs)
        return self.repository.save_token(new_token)

    def edit_token(self, token_id, **kwargs):
        token_to_edit = self.get_token_by_id(token_id)
        for key, value in kwargs.items():
            if key == "id":
                continue
            setattr(token_to_edit, key, value)
        merged = self.repository.save_token(token_to_edit)
        return merged

    def delete_token(self, token_id):
        token_to_delete = self.get_token_by_id(token_id)
        self.repository.delete_token(token_to_delete)
    
    def get_real_ip(self, request):
        if not request:
            return None

        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
        
        x_real_ip = request.headers.get('X-Real-IP')
        if x_real_ip:
            return x_real_ip
        
        return request.remote_addr

    def get_location_by_ip(self, ip_address):
        if not ip_address:
            return "Unknown location"

        if str(ip_address) in ["127.0.0.1", "localhost", "::1"]:
            return "Local Network"

        if str(ip_address).startswith(("192.168.", "10.", "172.")):
            return "Private Network"

        try:
            geo_reader = geoip2.database.Reader("app/static/geo/GeoLite2-City.mmdb")
            response = geo_reader.city(ip_address)
            city = response.city.name or "Unknown city"
            country = response.country.name or "Unknown country"
            return f"{city}, {country}"

        except Exception:
            return "Unknown location"

        finally:
            geo_reader.close()

    def get_device_name_by_request(self, request):
        ua_string = request.user_agent.string
        ua = parse(ua_string)

        os_info = (
            f"{
            ua.os.family} {
            ua.os.version_string}".strip()
            if ua.os.family
            else ""
        )
        browser_info = (
            f"{
            ua.browser.family} {
            ua.browser.version_string}".strip()
            if ua.browser.family
            else ""
        )

        if ua.is_mobile:
            if os_info:
                return f"{
                    ua.device.brand or 'Mobile'} {
                    ' - ' +
                    ua.device.model or ''} ({os_info})".strip()
            return f"{
                ua.device.brand or 'Mobile'} {
                ' - ' + ua.device.model or ''}".strip()

        if ua.is_tablet:
            if os_info:
                return f"{
                    ua.device.brand or 'Tablet'} {
                    ' - ' +
                    ua.device.model or ''} ({os_info})".strip()
            return f"{
                ua.device.brand or 'Tablet'} {
                ' - ' + ua.device.model or ''}".strip()

        if ua.is_pc:
            if os_info and browser_info:
                return f"Desktop - {os_info} ({browser_info})"
            elif os_info:
                return f"Desktop - {os_info}"
            else:
                return "Desktop"

        if ua.is_bot:
            return f"Bot - {ua.browser.family}" if ua.browser.family else "Bot"

        return "Unknown Device"


service = TokenService()
