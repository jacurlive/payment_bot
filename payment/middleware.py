import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware:
    """
    Middleware для ограничения доступа к API по IP адресам
    """

    def __init__(self, get_response):
        self.get_response = get_response

        import os
        from dotenv import load_dotenv
        load_dotenv()

        allowed_ips = os.getenv('ALLOWED_IPS', '127.0.0.1,::1')
        self.allowed_ips = [ip.strip() for ip in allowed_ips.split(',')]

        logger.info(f"IP Whitelist: {self.allowed_ips}")

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        if request.path.startswith('/api/'):

            if ip not in self.allowed_ips:
                logger.warning(f"Access denied for IP: {ip} to {request.path}")
                return JsonResponse(
                    {
                        'error': 'Access denied',
                        'message': 'Your IP address is not allowed to access this resource'
                    },
                    status=403
                )

        response = self.get_response(request)
        return response
