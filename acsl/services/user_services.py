import bcrypt
    
def normalize_workingarea(codes):
    """Ensure all workingarea codes are 7 digits by padding zeros to the right"""
    normalized = []
    for c in codes:
        c = str(c)
        if len(c) < 7:
            c = c.ljust(7, "0")
        normalized.append(c)
    return normalized
    
# --------------------------------------------------
# PASSWORD VALIDATION
# --------------------------------------------------
    
def validate_password(pw):
    if len(pw) < 8:
        return "Password must contain at least 8 characters."
    if not any(c.isupper() for c in pw):
        return "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in pw):
        return "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in pw):
        return "Password must contain at least one numeric character."
    return None


# --------------------------------------------------
# HASH PASSWORD
# --------------------------------------------------
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

