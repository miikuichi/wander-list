"""Small Supabase helper used by the project.

This module provides convenience helpers for creating an anon (client) and a
service-role client and for simple auth actions (sign up / sign in). It keeps
network calls out of startup-time so importing this module won't trigger any
remote calls until you explicitly call the helper functions.

Environment variables expected:
- SUPABASE_URL
- SUPABASE_KEY (anon/public key)
- SUPABASE_SERVICE_KEY (service role key with DB privileges)
"""

import os
from typing import Optional
from supabase import create_client, Client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def _ensure_url():
	if not SUPABASE_URL:
		raise RuntimeError("SUPABASE_URL is not set in the environment")


def get_anon_client() -> Client:
	"""Return a Supabase client using the anon/public key.

	Raises RuntimeError if required env vars are missing.
	"""
	_ensure_url()
	if not SUPABASE_ANON_KEY:
		raise RuntimeError("SUPABASE_KEY (anon key) is not set in the environment")
	return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_service_client() -> Client:
	"""Return a Supabase client using the service role key for privileged DB operations.

	The service role key should be kept secret and only used on the server.
	"""
	_ensure_url()
	if not SUPABASE_SERVICE_KEY:
		raise RuntimeError("SUPABASE_SERVICE_KEY (service role key) is not set in the environment")
	return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def sign_up(email: str, password: str) -> dict:
	"""Sign up a user with email + password using the anon client.

	Returns the raw response from Supabase python client. The shape depends on the
	installed supabase client version (usually a dict-like object with `user`/`session`).
	"""
	client = get_anon_client()
	# Using a dict payload keeps compatibility with multiple client versions
	return client.auth.sign_up({"email": email, "password": password})


def sign_in(email: str, password: str) -> dict:
	"""Sign in a user and return session information.

	This uses the anon client and returns whatever the Supabase client returns
	for a password sign-in (session + access token).
	"""
	client = get_anon_client()
	# Newer supabase-py versions use `sign_in_with_password`
	return client.auth.sign_in_with_password({"email": email, "password": password})


def get_user_from_token(access_token: str) -> Optional[dict]:
	"""Return user information for a given access token.

	Note: this performs a network call to Supabase auth. Returns None if token
	is falsy.
	"""
	if not access_token:
		return None
	client = get_anon_client()
	# The client usually exposes `auth.get_user` which accepts the token.
	try:
		return client.auth.get_user(access_token)
	except Exception:
		# Different versions expose different helpers; attempt the api route.
		try:
			return client.auth.api.get_user(access_token)
		except Exception:
			raise


def get_user_client(access_token: str):
	"""Return a Supabase client scoped to a user's access token when possible.

	Behavior:
	- If the installed supabase client exposes `auth.set_session`, this will be
	  used to attach the token to the client and the client is returned.
	- If that isn't available the function will still return the anon client but
	  attach a `__supabase_user_access_token__` attribute so callers can fall
	  back to using REST endpoints directly with the token.

	The exact behavior of using the returned client for authenticated requests
	depends on the `supabase` package version. This helper makes a best-effort
	attempt and returns an object users can work with.
	"""
	if not access_token:
		raise RuntimeError("access_token is required")
	client = get_anon_client()
	try:
		# Preferred method on newer clients
		if hasattr(client.auth, "set_session"):
			client.auth.set_session({"access_token": access_token})
			return client
		# Older clients may accept setting a `.session` field
		try:
			client.auth.session = {"access_token": access_token}
			return client
		except Exception:
			# fall through
			pass
	except Exception:
		# Ignore and fallback to marking the client
		pass

	# Attach the raw token for manual use (e.g., REST requests)
	setattr(client, "__supabase_user_access_token__", access_token)
	return client


__all__ = [
	"SUPABASE_URL",
	"SUPABASE_ANON_KEY",
	"SUPABASE_SERVICE_KEY",
	"get_anon_client",
	"get_service_client",
	"sign_up",
	"sign_in",
	"get_user_from_token",
]
