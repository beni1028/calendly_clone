from django.conf import settings
from django.urls import reverse
from rest_framework.authentication import TokenAuthentication
from rest_framework.reverse import reverse
from rest_framework import HTTP_HEADER_ENCODING, exceptions

from accounts.models import WebhookToken


class Webhook:
    model = WebhookToken

    def __init__(self, url_path, lookup_field=None):
        self.url_path = url_path
        self.lookup_field = lookup_field

    def __call__(self, cls):
        self.view_name = cls.__name__
        self.generate_token()
        cls.authentication_classes = [WebhooksAuthentication]
        return cls

    def generate_token(self):
        if not self.model.objects.filter(name=self.view_name,
                                         url=self.url_path,
                                         lookup_field=self.lookup_field).exists():
            self.model.objects.create(name=self.view_name,
                                      url=self.url_path,
                                      lookup_field=self.lookup_field)
    
    @staticmethod
    def generate_token_and_url_path(url_path, lookup_id=None):
        token = WebhookToken.objects.get(url=url_path)
        if lookup_id:
            url_path = url_path.replace('<' + token.lookup_field + '>', str(lookup_id))
        return f'Token {token.key}', url_path

def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, str):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


class WebhooksAuthentication(TokenAuthentication):

    keyword = 'Token'
    model = WebhookToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token, request)

    def get_model(self):
        if self.model is not None:
            return self.model
        from rest_framework.authtoken.models import Token
        return WebhookToken

    def get_detail(self, request, token_obj):
        lookup_field = token_obj.lookup_field
        return request.parser_context['kwargs'][lookup_field]

    def authenticate_credentials(self, key, request):
        model = self.get_model()
        try:
            token_obj = model.objects.get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(('Invalid token.'))

        # if token_obj.url not in request.build_absolute_uri():
        #     raise exceptions.AuthenticationFailed(('Invalid Authorizatin.'))
        print(token_obj.url, token_obj, reverse(
            "accounts:calendareventwebhookview",
            args=[self.get_detail(request, token_obj)]))
        return (token_obj.url, token_obj)

def get_token(url_path):
    # from accounts.model import WebhookToken

    token = WebhookToken.objects.get(url_path=url_path)
    return token