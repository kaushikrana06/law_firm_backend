import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data = {
            'error': {
                'message': str(exc),
                'code': getattr(exc, 'code', 'ERROR'),
                'details': response.data if isinstance(response.data, dict) else {}
            }
        }
        logger.error(f"API Error: {exc} - Context: {context['view'].__class__.__name__}")
    
    if isinstance(exc, ValidationError):
        response = Response(
            {
                'error': {
                    'message': 'Validation error',
                    'code': 'VALIDATION_ERROR',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return response