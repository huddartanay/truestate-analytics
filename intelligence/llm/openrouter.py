"""Bounded OpenRouter transport; no retrieval, prompts, logging or fallback.

Only caller-supplied synthetic evidence is used by the development benchmark.
Stage 16 owns production evidence transport and orchestration.
"""
import json
import os
import re
import socket
import time
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from pydantic import BaseModel, ValidationError
from intelligence.llm import openrouter_settings as settings


class ProviderError(RuntimeError):
    code = 'PROVIDER_ERROR'
    def __init__(self):
        super().__init__(self.code)

class MissingAPIKey(ProviderError): code = 'MISSING_API_KEY'
class AuthenticationError(ProviderError): code = 'AUTHENTICATION_FAILED'
class RateLimitError(ProviderError): code = 'RATE_LIMITED'
class ProviderTimeout(ProviderError): code = 'PROVIDER_TIMEOUT'
class ProviderUnavailable(ProviderError): code = 'PROVIDER_UNAVAILABLE'
class ModelUnavailable(ProviderError): code = 'MODEL_UNAVAILABLE'
class InvalidResponse(ProviderError): code = 'INVALID_RESPONSE'
class InvalidStructuredOutput(ProviderError): code = 'INVALID_STRUCTURED_OUTPUT'
class ConfigurationError(ProviderError): code = 'CONFIGURATION_FAILURE'
class ScopeRejected(ProviderError): code = 'SCOPE_REJECTED'


def key_present():
    return bool(os.environ.get('OPENROUTER_API_KEY', '').strip())


def check_model(model):
    if not isinstance(model, str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*', model) or model.startswith('openrouter/'):
        raise ConfigurationError()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ConfigurationError()


def error_for_status(status):
    return {401: AuthenticationError, 403: AuthenticationError, 402: ConfigurationError,
            404: ModelUnavailable, 408: ProviderTimeout, 429: RateLimitError,
            400: ConfigurationError, 422: ConfigurationError}.get(status, ProviderUnavailable)


def decimal_value(value):
    try:
        result = Decimal(str(value))
        if result.is_finite() and result >= 0:
            return result
    except (ValueError, InvalidOperation):
        pass
    return None


class OpenRouterClient:
    def __init__(self, timeout=settings.TIMEOUT_SECONDS):
        if type(timeout) not in (float, int) or not 1 <= timeout <= 180:
            raise ConfigurationError()
        # Refuse endpoint overrides instead of risking credential exfiltration.
        if os.environ.get('OPENROUTER_BASE_URL', settings.OPENROUTER_BASE_URL).rstrip('/') != settings.OPENROUTER_BASE_URL:
            raise ConfigurationError()
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, payload=None):
        if path != '/models' and path != '/chat/completions' and not re.fullmatch(r'/models/[a-z0-9.-]+/[a-zA-Z0-9_.-]+/endpoints', path):
            raise ConfigurationError()
        if (path == '/chat/completions') != (payload is not None):
            raise ConfigurationError()
        key = os.environ.get('OPENROUTER_API_KEY', '').strip() if payload is not None else ''
        if payload is not None and not key:
            raise MissingAPIKey()
        if key and (len(key) > 512 or not re.fullmatch(r'[A-Za-z0-9_.-]+', key)):
            raise ConfigurationError()
        body = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
        if body and (len(body) > 32_000 or key.encode() in body):
            raise ConfigurationError()
        headers = {'Content-Type': 'application/json'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        req = Request(settings.OPENROUTER_BASE_URL + path, data=body, headers=headers)
        failure = None
        raw = b''
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                if response.getcode() != 200:
                    failure = error_for_status(response.getcode())
                else:
                    raw = response.read(2_000_001)
        except HTTPError as exc:
            failure = error_for_status(exc.code)
            exc.close()  # Never read or print untrusted provider error bodies.
        except (TimeoutError, socket.timeout):
            failure = ProviderTimeout
        except URLError as exc:
            failure = ProviderTimeout if isinstance(exc.reason, TimeoutError) else ProviderUnavailable
        except ProviderError as exc:
            failure = type(exc)
        except Exception:
            failure = ProviderUnavailable
        # Raise outside except: no raw provider exception/credential in chaining.
        if failure:
            raise failure()
        if len(raw) > 2_000_000 or (key and key.encode() in raw):
            raise InvalidResponse()
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            data = None
        if not isinstance(data, dict):
            raise InvalidResponse()
        if data.get('error'):
            error = data['error']
            status = error.get('code') if isinstance(error, dict) else None
            raise error_for_status(status if type(status) is int else 503)()
        return data

    def chat(self, *, model, provider, provider_name, messages, output_type,
             response_models=(), pricing=None, max_tokens=settings.MAX_OUTPUT_TOKENS):
        check_model(model)
        if not isinstance(provider, str) or not re.fullmatch(r'[a-z0-9_-]+(?:/[a-z0-9_-]+)?', provider):
            raise ConfigurationError()
        if not isinstance(provider_name, str) or not provider_name or len(provider_name) > 80:
            raise ConfigurationError()
        if not isinstance(messages, list) or not 1 <= len(messages) <= 4 or type(max_tokens) is not int or not 1 <= max_tokens <= 1024:
            raise ConfigurationError()
        for item in messages:
            if not isinstance(item, dict) or set(item) != {'role', 'content'} or item['role'] not in ('system', 'user') or not isinstance(item['content'], str):
                raise ConfigurationError()
        if not isinstance(output_type, type) or not issubclass(output_type, BaseModel):
            raise ConfigurationError()
        payload = {'model': model, 'messages': messages, 'stream': False, 'temperature': 0,
                   'max_tokens': max_tokens,
                   'provider': {'only': [provider], 'allow_fallbacks': False,
                                'require_parameters': True, 'data_collection': 'deny', 'zdr': True},
                   'response_format': {'type': 'json_schema', 'json_schema': {
                       'name': 'truestate_contract', 'strict': True, 'schema': output_type.model_json_schema()}}}
        if pricing:
            pi, po = decimal_value(pricing.get('prompt')), decimal_value(pricing.get('completion'))
            if pi is None or po is None:
                raise ConfigurationError()
            payload['provider']['max_price'] = {'prompt': float(pi * 1_000_000), 'completion': float(po * 1_000_000)}
        started = time.perf_counter()
        data = self.request('/chat/completions', payload)
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        if data.get('model') not in {model, *response_models} or data.get('provider') != provider_name:
            raise InvalidResponse()
        choices = data.get('choices')
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise InvalidResponse()
        choice = choices[0]; message = choice.get('message')
        if not isinstance(message, dict) or not isinstance(message.get('content'), str) or len(message['content']) > 12000 or message.get('tool_calls'):
            raise InvalidResponse()
        content = message['content']
        valid = choice.get('finish_reason') == 'stop'
        try:
            parsed = output_type.model_validate_json(content)
        except (ValueError, ValidationError):
            parsed = None
        valid = valid and parsed is not None
        usage = data.get('usage', {})
        if not isinstance(usage, dict):
            raise InvalidResponse()
        counts = {k: usage.get(k) if type(usage.get(k)) is int and usage[k] >= 0 else None
                  for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        returned_cost = decimal_value(usage.get('cost'))
        input_cost = output_cost = None
        if pricing and counts['prompt_tokens'] is not None and counts['completion_tokens'] is not None:
            pi, po = decimal_value(pricing.get('prompt')), decimal_value(pricing.get('completion'))
            if pi is not None and po is not None:
                input_cost = pi * counts['prompt_tokens']; output_cost = po * counts['completion_tokens']
        # Reasoning, provider metadata, raw HTTP headers and untrusted errors are excluded.
        return {'content': content, 'contract': parsed.model_dump(mode='json') if valid else None,
                'structured_valid': valid, 'latency_ms': elapsed, 'usage': counts,
                'cost_usd': str(returned_cost) if returned_cost is not None else None,
                'input_cost_usd_calculated': str(input_cost) if input_cost is not None else None,
                'output_cost_usd_calculated': str(output_cost) if output_cost is not None else None,
                'model': data['model'], 'provider': data['provider'],
                'finish_reason': choice.get('finish_reason') if choice.get('finish_reason') in ('stop', 'length', 'content_filter') else 'OTHER'}

    def structured(self, **kwargs):
        result = self.chat(**kwargs)
        if not result['structured_valid']:
            raise InvalidStructuredOutput()
        return result


def validate_handoff(package):
    """Validate an already-created Stage 14 package, without routing or retrieval."""
    from intelligence.query.service import EvidencePackage
    try:
        package = EvidencePackage.model_validate(package)
    except ValueError:
        package = None
    if package is None or not package.can_generate or package.status.value not in ('AVAILABLE', 'PARTIAL') or not package.question:
        raise ScopeRejected()
    records = package.records + tuple(r for section in package.sections for r in section.records)
    ids = {e.reference_id for e in package.evidence}
    if not records or not ids or any(not r.evidence_ids or not set(r.evidence_ids) <= ids for r in records):
        raise ScopeRejected()
    return package


def production_generate(package, messages, output_type):
    validate_handoff(package)
    if not settings.OPENROUTER_MODEL or settings.OPENROUTER_MODEL != settings.SELECTED_MODEL or not settings.SELECTED_PROMPT_STRATEGY or not settings.SELECTED_PROVIDER:
        raise ConfigurationError()
    # Stage 16 supplies messages/output schema; this layer never builds them.
    return OpenRouterClient().structured(model=settings.OPENROUTER_MODEL, messages=messages,
                                        output_type=output_type, **settings.SELECTED_PROVIDER)
