"""
Avatar Helper Functions
Generate initials-based avatars for users
"""

def get_user_initials(username):
    """Get user initials from username"""
    if not username:
        return "?"
    
    parts = username.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    elif len(parts) == 1:
        return username[:2].upper()
    else:
        return "?"

def get_avatar_color(username):
    """Generate a consistent color for a username"""
    colors = [
        '#1abc9c', '#2ecc71', '#3498db', '#9b59b6', '#34495e',
        '#16a085', '#27ae60', '#2980b9', '#8e44ad', '#2c3e50',
        '#f1c40f', '#e67e22', '#e74c3c', '#ecf0f1', '#95a5a6',
        '#f39c12', '#d35400', '#c0392b', '#bdc3c7', '#7f8c8d',
        '#d4af37', '#e6c85c', '#2c3e50', '#1a2332', '#3a4a5f'
    ]
    
    # Generate a hash from username to pick color consistently
    hash_val = sum(ord(c) for c in username)
    return colors[hash_val % len(colors)]
