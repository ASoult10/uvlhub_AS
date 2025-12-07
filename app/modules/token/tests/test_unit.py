from datetime import datetime

import pytest
from flask import request
from flask_jwt_extended import decode_token

from app import db
from app.modules.auth.models import User
from app.modules.token.models import Token, TokenType
from app.modules.token.services import TokenService

token_service = TokenService()

PARENT_TOKEN_JTI = "parent-example-jti"  # Example parent JTI for testing
PARENT_TOKEN_ID = 2  # Example parent token ID for testing
PARENT_TOKEN_CODE = "parent-example-code"  # Example parent code for testing
PARENT_TOKEN_IS_ACTIVE = True  # Example parent active status for testing
PARENT_TOKEN_TYPE = TokenType.REFRESH_TOKEN  # Example parent token type for testing
PARENT_TOKEN_EXPIRES_AT = datetime.fromisoformat("2025-12-31T23:59:59")  # Example parent expiration date for testing
PARENT_TOKEN_DEVICE_INFO = "Parent Test Device"  # Example parent device info for testing
PARENT_TOKEN_LOCATION_INFO = "Parent Test Location"  # Example parent location info for testing

TOKEN_ID = 1  # Example token ID for testing
TOKEN_JTI = "example-jti"  # Example JTI for testing
TOKEN_CODE = "example-code"  # Example code for testing
TOKEN_IS_ACTIVE = True  # Example active status for testing
TOKEN_TYPE = TokenType.ACCESS_TOKEN  # Example token type for testing
TOKEN_EXPIRES_AT = datetime.fromisoformat("2024-12-31T23:59:59")  # Example expiration date for testing
TOKEN_DEVICE_INFO = "Test Device"  # Example device info for testing
TOKEN_LOCATION_INFO = "Test Location"  # Example location info for testing
TOKEN_PARENT_JTI = PARENT_TOKEN_JTI  # Example token parent JTI for testing

USER_ID = 1  # Example user ID for testing
USER_EMAIL = "test@example.com"  # Example user email for testing
USER_PASSWORD = "test1234"  # Example user password for testing
USER_USERNAME = "testuser"  # Example user username for testing


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        user = User.query.filter_by(email=USER_EMAIL).first()
        if not user:
            user = User(email=USER_EMAIL, password=USER_PASSWORD, username=USER_USERNAME, id=USER_ID)
            db.session.add(user)
            db.session.commit()

        existing = Token.query.filter(Token.jti.in_([TOKEN_JTI, PARENT_TOKEN_JTI, 2 * TOKEN_JTI])).all()
        for e in existing:
            db.session.delete(e)
        db.session.commit()

        test_parent_token = Token(
            id=PARENT_TOKEN_ID,
            jti=PARENT_TOKEN_JTI,
            code=PARENT_TOKEN_CODE,
            is_active=PARENT_TOKEN_IS_ACTIVE,
            type=PARENT_TOKEN_TYPE,
            expires_at=PARENT_TOKEN_EXPIRES_AT,
            device_info=PARENT_TOKEN_DEVICE_INFO,
            location_info=PARENT_TOKEN_LOCATION_INFO,
            user_id=USER_ID,
        )

        test_token = Token(
            id=TOKEN_ID,
            jti=TOKEN_JTI,
            code=TOKEN_CODE,
            is_active=TOKEN_IS_ACTIVE,
            type=TOKEN_TYPE,
            expires_at=TOKEN_EXPIRES_AT,
            device_info=TOKEN_DEVICE_INFO,
            location_info=TOKEN_LOCATION_INFO,
            parent_jti=TOKEN_PARENT_JTI,
            user_id=USER_ID,
        )

        db.session.add(test_parent_token)
        db.session.add(test_token)
        db.session.commit()

    yield test_client


def test_get_token_by_id(test_client):
    """
    Sample test to verify the get_token_by_id function.
    """
    token = token_service.get_token_by_id(TOKEN_ID)
    assert token is None or token.id == TOKEN_ID, "The token ID does not match the requested ID."


def test_get_token_by_jti(test_client):
    """
    Sample test to verify the get_token_by_jti function.
    """
    token = token_service.get_token_by_jti(TOKEN_JTI)
    assert token is None or token.jti == TOKEN_JTI, "The token JTI does not match the requested JTI."


def test_pairs_of_tokens_by_jti(test_client):
    """
    Sample test to verify the get_pair_of_tokens_by_jti function.
    """
    access_token, refresh_token = token_service.get_pair_of_tokens_by_jti(TOKEN_JTI)
    if access_token:
        assert access_token.jti == TOKEN_JTI, "The access token JTI does not match the requested JTI."
    if refresh_token:
        assert refresh_token.jti == TOKEN_PARENT_JTI, "The refresh token JTI does not match the expected parent JTI."


def test_get_active_tokens_by_user(test_client):
    """
    Sample test to verify the get_active_tokens_by_user function.
    """
    tokens = token_service.get_active_tokens_by_user(USER_ID)
    for token in tokens:
        assert token.is_active, "Found an inactive token in the active tokens list."
        assert token.user_id == USER_ID, "Found a token that does not belong to the specified user."


def test_get_all_tokens_by_user(test_client):
    """
    Sample test to verify the get_all_tokens_by_user function.
    """
    tokens = token_service.get_all_tokens_by_user(USER_ID)
    for token in tokens:
        assert token.user_id == USER_ID, "Found a token that does not belong to the specified user."


def test_revoke_token(test_client):
    """
    Sample test to verify the revoke_token function.
    """
    result = token_service.revoke_token(TOKEN_ID, USER_ID)
    assert result is True, "Failed to revoke the token."
    token, parent_token = token_service.get_pair_of_tokens_by_jti(TOKEN_JTI)
    if token:
        assert not token.is_active, "The token is still active after revocation."
    if parent_token:
        assert not parent_token.is_active, "The parent token is still active after revocation."
    token_service.edit_token(TOKEN_ID, is_active=True)
    token_service.edit_token(PARENT_TOKEN_ID, is_active=True)


def test_revoke_token_invalid_user(test_client):
    """
    Sample test to verify the revoke_token function with an invalid user.
    """
    result = token_service.revoke_token(TOKEN_ID, USER_ID + 1)
    assert result is False, "Token revocation should have failed for an invalid user."
    token, parent_token = token_service.get_pair_of_tokens_by_jti(TOKEN_JTI)
    if token:
        assert token.is_active, "The token should still be active after failed revocation attempt."
    if parent_token:
        assert parent_token.is_active, "The parent token should still be active after failed revocation attempt."
    token_service.edit_token(TOKEN_ID, is_active=True)
    token_service.edit_token(PARENT_TOKEN_ID, is_active=True)


def test_revoke_all_tokens_for_user(test_client):
    """
    Sample test to verify the revoke_all_tokens_for_user function.
    """
    revoked_count = token_service.revoke_all_tokens_for_user(USER_ID)
    assert revoked_count > 0, "No tokens were revoked."
    tokens = token_service.get_all_tokens_by_user(USER_ID)
    for token in tokens:
        assert not token.is_active, "Found an active token after revoking all tokens for the user."


def test_create_tokens(test_client):
    """
    Sample test to verify the create_tokens function.
    """
    device_info = 2 * TOKEN_DEVICE_INFO
    location_info = 2 * TOKEN_LOCATION_INFO
    access_token, refresh_token = token_service.create_tokens(USER_ID, device_info, location_info)
    assert access_token is not None, "Access token was not created."
    assert refresh_token is not None, "Refresh token was not created."


def test_refresh_access_token_uses_jti_and_saves_record(test_client):
    """
    Sample test to verify the refresh_access_token function.
    """
    _, refresh_token_str = token_service.create_tokens(USER_ID, TOKEN_DEVICE_INFO, TOKEN_LOCATION_INFO)
    decoded_refresh = decode_token(refresh_token_str)
    refresh_jti = decoded_refresh.get("jti")
    assert refresh_jti is not None

    new_access_token_str = token_service.refresh_access_token(
        USER_ID, TOKEN_DEVICE_INFO, TOKEN_LOCATION_INFO, refresh_jti
    )
    assert new_access_token_str is not None

    decoded_new = decode_token(new_access_token_str)
    new_jti = decoded_new.get("jti")
    assert new_jti is not None

    new_record = token_service.get_token_by_jti(new_jti)
    assert new_record is not None, "New access token record was not saved in the database."
    assert new_record.parent_jti == refresh_jti, "New access token's parent JTI does not match the refresh token JTI."
    assert new_record.user_id == USER_ID, "New access token's user ID does not match."


def test_save_token(test_client):
    """
    Sample test to verify the save_token function.
    """
    new_token = Token(
        id=None,
        jti=3 * TOKEN_JTI,
        code=3 * TOKEN_CODE,
        is_active=True,
        type=TokenType.ACCESS_TOKEN,
        expires_at=TOKEN_EXPIRES_AT,
        device_info=2 * TOKEN_DEVICE_INFO,
        location_info=2 * TOKEN_LOCATION_INFO,
        user_id=USER_ID,
    )
    saved_token = token_service.save_token(
        id=new_token.id,
        code=new_token.code,
        is_active=new_token.is_active,
        type=new_token.type,
        expires_at=new_token.expires_at,
        device_info=new_token.device_info,
        location_info=new_token.location_info,
        user_id=new_token.user_id,
        jti=new_token.jti,
    )
    assert saved_token.id is not None, "Saved token does not have an ID."
    assert saved_token.jti == 3 * TOKEN_JTI, "Saved token JTI does not match."
    assert saved_token.code == 3 * TOKEN_CODE, "Saved token code does not match."
    assert saved_token.is_active is True, "Saved token active status does not match."
    assert saved_token.type == TokenType.ACCESS_TOKEN, "Saved token type does not match."
    assert saved_token.device_info == 2 * TOKEN_DEVICE_INFO, "Saved token device info does not match."
    assert saved_token.location_info == 2 * TOKEN_LOCATION_INFO, "Saved token location info does not match."


def test_edit_token(test_client):
    """Sample test to verify the edit_token function."""
    token_to_edit = token_service.get_token_by_id(TOKEN_ID)
    if token_to_edit is None:
        pytest.skip("Token to edit does not exist.")
    new_device_info = 2 * TOKEN_DEVICE_INFO
    edited_token = token_service.edit_token(TOKEN_ID, device_info=new_device_info, id=TOKEN_ID + 1)
    assert edited_token.device_info == new_device_info, "Token device info was not updated."
    assert edited_token.id == TOKEN_ID, "Edited token ID does not match."
    assert edited_token.code == token_to_edit.code, "Edited token code should not have changed."
    assert edited_token.is_active == token_to_edit.is_active, "Edited token active status should not have changed."
    assert edited_token.type == token_to_edit.type, "Edited token type should not have changed."
    assert (
        edited_token.location_info == token_to_edit.location_info
    ), "Edited token location info should not have changed."


def test_delete_token(test_client):
    """Sample test to verify the delete_token function."""
    token_to_delete = Token(
        id=None,
        jti=2 * TOKEN_JTI,
        code=2 * TOKEN_CODE,
        is_active=True,
        type=TokenType.ACCESS_TOKEN,
        expires_at=TOKEN_EXPIRES_AT,
        device_info=2 * TOKEN_DEVICE_INFO,
        location_info=2 * TOKEN_LOCATION_INFO,
        user_id=USER_ID,
    )
    saved_token = token_service.save_token(
        id=token_to_delete.id,
        code=token_to_delete.code,
        is_active=token_to_delete.is_active,
        type=token_to_delete.type,
        expires_at=token_to_delete.expires_at,
        device_info=token_to_delete.device_info,
        location_info=token_to_delete.location_info,
        user_id=token_to_delete.user_id,
        jti=token_to_delete.jti,
    )
    token_id = saved_token.id
    token_service.delete_token(saved_token.id)
    deleted_token = token_service.get_token_by_id(token_id)
    assert deleted_token is None, "Token was not deleted successfully."


def test_get_location_by_ip(test_client):
    """
    Sample test to verify the get_location_by_ip function.
    """
    non_location = token_service.get_location_by_ip(None)
    assert non_location == "Unknown location", "Location for None IP should be 'Unknown location'."

    local_ip_address = "127.0.0.1"
    local_location = token_service.get_location_by_ip(local_ip_address)
    assert local_location == "Local Network", "Location for localhost IP should be 'Local Network'."

    private_ip_address = "192.168.1.1"
    private_location = token_service.get_location_by_ip(private_ip_address)
    assert private_location == "Private Network", "Location for private IP should be 'Private Network'."

    public_ip_address = "79.117.197.244"
    public_location = token_service.get_location_by_ip(public_ip_address)
    assert public_location == "Dos Hermanas, Spain", "Location for public IP should be 'Dos Hermanas, Spain'."

    error_ip_address = "999.999.999.999"
    error_location = token_service.get_location_by_ip(error_ip_address)
    assert error_location == "Unknown location", "Location for invalid IP should be 'Unknown location'."


def test_get_computer_name_by_request(test_client):
    """
    Sample test to verify the get_device_name_by_request function.
    """
    with test_client.application.test_request_context(
        "/",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        },
    ):
        device_name = token_service.get_device_name_by_request(request)
        assert (
            "Windows" in device_name or "Chrome" in device_name
        ), "Device name should contain OS or browser information."


def test_get_mobile_name_by_request(test_client):
    """
    Sample test to verify the get_device_name_by_request function for mobile user agents.
    """
    with test_client.application.test_request_context(
        "/",
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
        },
    ):
        device_name = token_service.get_device_name_by_request(request)
        assert (
            "iPhone" in device_name or "Mobile" in device_name
        ), "Device name should contain mobile device information."


def test_get_unknown_name_by_request(test_client):
    """
    Sample test to verify the get_device_name_by_request function for unknown user agents.
    """
    with test_client.application.test_request_context("/", headers={"User-Agent": ""}):
        device_name = token_service.get_device_name_by_request(request)
        assert device_name == "Unknown Device", "Device name should be 'Unknown Device' for empty user agent."


def test_get_tablet_name_by_request(test_client):
    """
    Sample test to verify the get_device_name_by_request function for tablet user agents.
    """
    with test_client.application.test_request_context(
        "/",
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-T865) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.89 Safari/537.36"
        },
    ):
        device_name = token_service.get_device_name_by_request(request)
        assert (
            "SM-T865" in device_name or "Tablet" in device_name
        ), "Device name should contain tablet device information."


def test_get_bot_name_by_request(test_client):
    """
    Sample test to verify the get_device_name_by_request function for bot user agents.
    """
    with test_client.application.test_request_context(
        "/", headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
    ):
        device_name = token_service.get_device_name_by_request(request)
        assert "Googlebot" in device_name or "Bot" in device_name, "Device name should contain bot information."


def test_get_token_sessions_route(test_client):
    """
    Sample test to verify the /token/sessions route.
    """
    # Asegurarse de que el usuario existe
    with test_client.application.app_context():
        user = User.query.filter_by(email=USER_EMAIL).first()
        assert user is not None

    # Simular login inyectando la sesión
    with test_client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    response = test_client.get("/token/sessions")
    assert response.status_code == 302, "Failed to access the /token/sessions route."


def test_revoke_token_route(test_client):
    """
    Sample test to verify the /token/revoke route.
    """
    # Asegurarse de que el usuario existe
    with test_client.application.app_context():
        user = User.query.filter_by(email=USER_EMAIL).first()
        assert user is not None

    # Simular login inyectando la sesión
    with test_client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    response = test_client.post("/token/revoke/" + str(TOKEN_ID))
    assert response.status_code == 302, "Failed to access the /token/revoke route."


def test_revoke_all_tokens_route(test_client):
    """
    Sample test to verify the /token/revoke_all route.
    """
    # Asegurarse de que el usuario existe
    with test_client.application.app_context():
        user = User.query.filter_by(email=USER_EMAIL).first()
        assert user is not None

    # Simular login inyectando la sesión
    with test_client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    response = test_client.post("/token/revoke_all")
    assert response.status_code == 302, "Failed to access the /token/revoke_all route."
