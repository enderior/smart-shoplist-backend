import logging
import dns.resolver

logger = logging.getLogger(__name__)


def check_mx_record(email: str) -> bool:
    """
    Мягкая проверка MX-записи домена.
    Возвращает True, если MX есть или проверить не удалось.
    Возвращает False только если MX точно нет.
    """
    try:
        domain = email.split("@")[1]
    except IndexError:
        return False

    try:
        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0
    except dns.resolver.NXDOMAIN:
        logger.warning(f"MX-запись не найдена для домена: {domain}")
        return False
    except dns.resolver.NoAnswer:
        logger.warning(f"Нет MX-записи для домена: {domain}")
        return False
    except Exception as e:
        # Если DNS-сервер недоступен или timeout — не блокируем пользователя
        logger.warning(f"Не удалось проверить MX для {domain}: {e}")
        return True
