TEST_EMAIL_DOMAINS = {
    'example.com',
    'example.org',
    'example.net',
    'mailinator.com',
}

TEST_EMAIL_PREFIXES = (
    'test',
    'qa',
    'demo',
    'preview',
    'seed',
    'sample',
    'fake',
    'mock',
)


def email_is_test_data(email: str) -> bool:
    normalized = (email or '').strip().lower()
    if '@' not in normalized:
        return False

    local_part, domain = normalized.split('@', 1)
    if domain in TEST_EMAIL_DOMAINS or domain.endswith('.test'):
        return True

    if local_part.startswith(TEST_EMAIL_PREFIXES):
        return True

    plus_tag = local_part.split('+', 1)[1] if '+' in local_part else ''
    return plus_tag.startswith(TEST_EMAIL_PREFIXES)