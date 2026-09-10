from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from schemas.user import TokenData
from service.auth_service import auth_service

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> TokenData:
    """Extrai e valida o token JWT do header Authorization."""
    token = credentials.credentials
    return auth_service.decode_token(token)


def require_roles(*allowed_roles: str):
    """
    Retorna uma dependência que verifica se o usuário logado
    possui uma das roles permitidas.

    Exemplo de uso no router:
        @router.get("/admin-only", dependencies=[Depends(require_roles("ADMIN"))])
    """

    async def _check_role(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para acessar este recurso",
            )
        return current_user

    return _check_role
