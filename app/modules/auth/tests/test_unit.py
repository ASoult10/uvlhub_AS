import base64
import time

import pyotp
import pytest
from flask import url_for
from app import db
from app import limiter

from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.profile.repositories import UserProfileRepository


@pytest.fixture
def app_with_rate_limit(test_client):
    """
    Fixture to temporarily enable rate limiting for a test.
    """
    # Habilita el limitador para el test
    limiter.enabled = True
    # Reinicia el estado del limitador para asegurar un estado limpio
    limiter.reset()
    
    yield test_client
    
    # Deshabilita el limitador después del test
    limiter.enabled = False


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_login_success(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path != url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_email(test_client):
    response = test_client.post(
        "/login", data=dict(email="bademail@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_password(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="basspassword"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_rate_limit(app_with_rate_limit):
    """
    Tests that the login route is rate-limited after 3 failed POST attempts.
    """
    # The first 3 attempts should be allowed (status 200, re-rendering the form)
    for _ in range(3):
        response = app_with_rate_limit.post(
            "/login", data=dict(email="bad@example.com", password="badpassword")
        )
        assert response.status_code == 200
        assert b"Invalid credentials" in response.data

    # The 4th attempt should be rate-limited (status 429)
    response = app_with_rate_limit.post(
        "/login", data=dict(email="bad@example.com", password="badpassword")
    )
    assert response.status_code == 429
    assert b"You have exceeded the login attempt limit" in response.data


def test_login_rate_limit_resets_on_success(app_with_rate_limit):
    """
    Tests that the rate limit is reset after a successful login.
    """
    # Make 2 failed attempts
    for _ in range(2):
        response = app_with_rate_limit.post(
            "/login", data=dict(email="test@example.com", password="wrongpassword")
        )
        assert response.status_code == 200

    # Make a successful attempt
    response = app_with_rate_limit.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path != url_for("auth.login"), "Successful login failed"

    # Logout
    app_with_rate_limit.get("/logout", follow_redirects=True)

    # The rate limit should now be reset. We should have 3 new attempts.
    for i in range(3):
        response = app_with_rate_limit.post(
            "/login", data=dict(email="test@example.com", password="wrongpassword")
        )
        assert response.status_code == 200, f"Attempt {i+1} should have been allowed"

    # The 4th attempt should now be blocked
    response = app_with_rate_limit.post(
        "/login", data=dict(email="test@example.com", password="wrongpassword")
    )
    assert response.status_code == 429


def test_login_get_requests_not_limited(app_with_rate_limit):
    """
    Tests that GET requests to the login page do not trigger the rate limit.
    """
    for _ in range(5):
        response = app_with_rate_limit.get("/login")
        assert response.status_code == 200
    
    # A subsequent POST should still be allowed
    response = app_with_rate_limit.post("/login", data=dict(email="bad@example.com", password="bad"))
    assert response.status_code == 200


def test_signup_user_no_name(test_client):
    response = test_client.post(
        "/signup/", data=dict(surname="Foo", email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert b"This field is required" in response.data, response.data


def test_signup_user_unsuccessful(test_client):
    email = "test@example.com"
    response = test_client.post(
        "/signup/", data=dict(name="Test", surname="Foo", email=email, password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert f"Email {email} in use".encode("utf-8") in response.data


def test_signup_user_successful(test_client):
    response = test_client.post(
        "/signup/",
        data=dict(name="Foo", surname="Example", email="foo@example.com", password="foo1234"),
        follow_redirects=True,
    )
    assert response.request.path == url_for("public.index"), "Signup was unsuccessful"


def test_service_create_with_profie_success(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "service_test@example.com", "password": "test1234"}

    AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1


def test_service_create_with_profile_fail_no_email(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "", "password": "1234"}

    with pytest.raises(ValueError, match="Email is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_service_create_with_profile_fail_no_password(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "test@example.com", "password": ""}

    with pytest.raises(ValueError, match="Password is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


#2FA

def test_generate_qr_code_uri():
    uri = "otpauth://totp/test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test"
    qr_b64 = AuthenticationService().generate_qr_code_uri(uri)

    # Should be a base64 string that decodes to a PNG image (PNG signature starts with 0x89 0x50 0x4E 0x47)
    assert isinstance(qr_b64, str)
    img_bytes = base64.b64decode(qr_b64)
    assert img_bytes[:4] == b"\x89PNG"

def test_generate_qr_code_uri():
    uri = "otpauth://totp/test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test"
    qr_b64 = AuthenticationService().generate_qr_code_uri(uri)

    # Should be a base64 string that decodes to a PNG image (PNG signature starts with 0x89 0x50 0x4E 0x47)
    assert isinstance(qr_b64, str)
    img_bytes = base64.b64decode(qr_b64)
    assert img_bytes[:4] == b"\x89PNG"


def test_check_temp_code_success():
    """Test the authentication service check_temp_code method."""
    # Create a user and set a known secret
    user = AuthenticationService().create_with_profile(
        name="Test", surname="User", email="totp_test@example.com", password="test1234"
    )
    secret = pyotp.random_base32()
    user.set_user_secret(secret)
    db.session.add(user)
    db.session.commit()

    # Generate current TOTP code
    totp = pyotp.TOTP(secret).now()
    
    # Test that the code validates when user is logged in
    # We simulate this by using the service with a mock current_user context
    from unittest.mock import patch
    with patch('app.modules.auth.services.current_user', user):
        assert AuthenticationService().check_temp_code(totp) is True
        
def test_2fa_verify_route_invalid_code(test_client, clean_database):
    # Create a user
    email = "2fa_test2@example.com"
    password = "test1234"
    AuthenticationService().create_with_profile(name="Two", surname="Fa", email=email, password=password)

    # Ensure the user has some secret
    user = UserRepository().get_by_email(email)
    secret = pyotp.random_base32()
    user.set_user_secret(secret)
    db.session.add(user)
    db.session.commit()

    # Login the user
    resp = test_client.post("/login", data=dict(email=email, password=password), follow_redirects=True)
    assert resp.status_code in (200, 302)

    # Post an invalid code
    resp = test_client.post("/2fa-setup/verify", data=dict(code="000000"), follow_redirects=True)
    assert resp.request.path == url_for("auth.two_factor_setup")
    assert b"Invalid verification code" in resp.data
