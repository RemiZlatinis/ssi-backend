# Authentication Flow & Architecture

## Overview

The authentication system is designed to be **headless** (API-only) and **RESTful**, using **JWTs** (JSON Web Tokens) for session management. It leverages a combination of powerful Django packages to achieve this without reinventing the wheel.

## Core Components

### 1. Django AllAuth (`django-allauth`)

- **Role**: The "Engine".
- **Purpose**: Handles the complex logic of user registration, account management, and social authentication (OAuth2). It manages the `User` and `SocialAccount` models.
- **Headless Mode**: `HEADLESS_ONLY = True` is enabled to disable `allauth`'s default template-based views, ensuring it acts purely as a backend logic provider.

### 2. DJ Rest Auth (`dj_rest_auth`)

- **Role**: The "Bridge" / "API Layer".
- **Purpose**: Exposes `django-allauth`'s functionality as REST API endpoints.
- **Why it's needed**: `django-allauth` (historically) only provided template-based views. `dj_rest_auth` wraps these into JSON-speaking API views (e.g., `/api/auth/login/`, `/api/auth/google/`).
- **Configuration**: Configured to use JWTs via `REST_AUTH = {'USE_JWT': True}`.

### 3. Simple JWT (`rest_framework_simplejwt`)

- **Role**: The "Token Provider".
- **Purpose**: Generates, validates, and manages JWTs (Access and Refresh tokens).
- **Integration**: Used by `dj_rest_auth` to issue tokens upon successful login.

### 4. DRF Auth Token (`rest_framework.authtoken`)

- **Role**: Dependency / Legacy Support.
- **Purpose**: Provides standard database-backed tokens.
- **Why it's here**: It is a required dependency for `dj_rest_auth` (and `django-rest-framework` generally) to function correctly, even when JWTs are the primary method. It provides the underlying `Token` model structure that `dj_rest_auth` might reference internally or as a fallback.

## Authentication Flow

1.  **Client** (Mobile/Web) sends credentials (username/password or Google Auth Code) to `api/auth/`.
2.  **`dj_rest_auth`** views receive the request.
3.  **`django-allauth`** validates the credentials or verifies the social token with Google.
4.  If valid, **`simplejwt`** generates an Access Token and a Refresh Token.
5.  **Response** returns these tokens to the client.
6.  **Client** uses the Access Token in the `Authorization: Bearer <token>` header for subsequent requests.

## Settings Explained

### Django AllAuth

```python
ACCOUNT_AUTHENTICATION_METHOD = "username_email"  # Flexible login (user can use either)
ACCOUNT_EMAIL_REQUIRED = True                     # Email is the primary identifier
ACCOUNT_USERNAME_REQUIRED = False                 # Username is secondary/optional
ACCOUNT_EMAIL_VERIFICATION = "none"               # No email confirmation loop (simplifies onboarding)
SOCIALACCOUNT_AUTO_SIGNUP = True                  # One-click social register (no extra "confirm details" step)
HEADLESS_ONLY = True                              # Disables standard HTML views (Critical for API-only)
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True         # Security: Merges social login with existing email account
```

### DRF & JWT

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",  # Enforce JWT for all protected views
    ),
}

REST_AUTH = {
    "USE_JWT": True,                                              # Switch dj_rest_auth to JWT mode
    "JWT_AUTH_REFRESH_COOKIE": None,                              # Send refresh token in JSON body (easier for mobile apps)
    "USER_DETAILS_SERIALIZER": "authentication.serializers...",   # Custom serializer to return extra data (e.g. avatar)
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=365),  # Long-lived tokens (Dev/MVP choice)
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),
}
```

## Customizations (`authentication` app)

- **`CustomUserDetailsSerializer`**: Extends the default user response to include the `picture` from the linked Google SocialAccount.
- **`GoogleLogin` View**: A custom view inheriting from `SocialLoginView` to wire up the Google adapter.
- **`CustomGoogleOAuth2Client`**: A hotfix class to resolve a compatibility issue between `django-allauth` and `dj_rest_auth` regarding scope handling.
