"""
Authentication utilities for Veloce API
Handles login and token management
"""

import requests
from typing import Dict
from VeloceAgent.config import VELOCE_API_BASE_URL


def authenticate_veloce(email: str, password: str) -> Dict[str, str]:
    """
    Authenticate with Veloce API and get access token.
    
    Args:
        email: Veloce account email
        password: Veloce account password
        
    Returns:
        Dictionary with token and user info
        
    Raises:
        Exception if authentication fails
    """
    try:
        response = requests.post(
            f"{VELOCE_API_BASE_URL}/users/authenticate",
            json={
                "email": email,
                "password": password
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "token": data.get("token"),
            "user_id": data.get("id"),
            "email": data.get("email"),
            "first_name": data.get("firstName"),
            "last_name": data.get("lastName")
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception("Invalid email or password")
        else:
            raise Exception(f"Authentication failed: {e.response.status_code}")
    except Exception as e:
        raise Exception(f"Authentication error: {str(e)}")


def refresh_token(current_token: str) -> str:
    """
    Refresh the Veloce API access token.
    
    Args:
        current_token: Current valid token
        
    Returns:
        New access token
    """
    try:
        response = requests.post(
            f"{VELOCE_API_BASE_URL}/users/refreshToken",
            headers={"Authorization": f"Bearer {current_token}"}
        )
        response.raise_for_status()
        data = response.json()
        
        return data.get("token")
        
    except Exception as e:
        raise Exception(f"Token refresh failed: {str(e)}")


def get_user_locations(token: str) -> list:
    """
    Get all locations the user has access to.
    
    Args:
        token: Valid Veloce API token
        
    Returns:
        List of location dictionaries
    """
    try:
        response = requests.get(
            f"{VELOCE_API_BASE_URL}/locations",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        locations = response.json()
        
        # Format location info
        return [
            {
                "id": loc.get("id"),
                "name": loc.get("name"),
                "licence_number": loc.get("licenceNumber"),
                "is_active": loc.get("isActive", False),
                "city": loc.get("city"),
                "address": loc.get("address")
            }
            for loc in locations
        ]
        
    except Exception as e:
        raise Exception(f"Failed to fetch locations: {str(e)}")
