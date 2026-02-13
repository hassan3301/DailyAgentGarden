"""
Location configuration mapping for Pur & Simple restaurants
Maps friendly location names to their Secret Manager keys and location IDs
"""

LOCATION_CONFIG = {
    "appleby": {
        "name": "PUR & SIMPLE #006",
        "secret_email": "veloce-appleby-email",
        "secret_password": "veloce-appleby-password",
        "location_id": "11eb3645-fa16-6b91-9e61-0242ac130002"
    },
    "heartland": {
        "name": "PUR & SIMPLE #026",
        "secret_email": "veloce-heartland-email",
        "secret_password": "veloce-heartland-password",
        "location_id": "11ec01dd-871d-d0ef-bcaf-0242ac130005"
    },
    "fairview": {
        "name": "PUR & SIMPLE #046",
        "secret_email": "veloce-fairview-email",
        "secret_password": "veloce-fairview-password",
        "location_id": "11ef07e0-4e6f-972a-a5b8-0242ac13000c"
    },
    "waterdown": {
        "name": "PUR & SIMPLE #073",
        "secret_email": "veloce-waterdown-email",
        "secret_password": "veloce-waterdown-password",
        "location_id": "11f0bfe7-5b2f-c422-99ef-26b66be7d8ed"
    },
    "gateway": {
        "name": "PUR & SIMPLE #063",
        "secret_email": "veloce-gateway-email",
        "secret_password": "veloce-gateway-password",
        "location_id": "11f0930f-9883-612f-a585-4e12e8bcccff"
    }
}


def get_location_list():
    """Get list of locations for dropdown in frontend"""
    return [
        {"key": key, "name": config["name"]} 
        for key, config in LOCATION_CONFIG.items()
    ]


def get_location_config(location_key: str):
    """Get configuration for a specific location"""
    if location_key not in LOCATION_CONFIG:
        raise ValueError(f"Unknown location: {location_key}. Valid options: {list(LOCATION_CONFIG.keys())}")
    return LOCATION_CONFIG[location_key]