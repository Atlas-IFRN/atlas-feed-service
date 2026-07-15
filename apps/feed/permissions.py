from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """
    Leitura liberada para qualquer autenticado. Escrita "de dono" (editar/apagar
    o próprio recurso) só para quem tem `author_id == request.user.id`.

    Aplica a checagem de autoria apenas às ações padrão de mutação do recurso
    (update/partial_update/destroy). Ações custom como `like`/`comments`
    (curtir ou comentar o post de OUTRA pessoa) não são bloqueadas aqui — basta
    estar autenticado.
    """

    message = "Apenas o autor pode modificar este recurso."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if getattr(view, 'action', None) in ('update', 'partial_update', 'destroy'):
            return str(obj.author_id) == str(request.user.id)
        return True


def is_teacher(user):
    """Só docentes (ou staff/admin) — mesma regra usada para fixar posts."""
    return (getattr(user, 'role', '') or '').upper() == 'TEACHER' or \
        getattr(user, 'is_staff', False)


class IsTeacher(BasePermission):
    """Permite acesso somente a usuários autenticados com papel de professor."""

    message = "Apenas professores podem acessar este recurso."

    def has_permission(self, request, view):
        user = request.user
        role = str(getattr(user, 'role', '') or '').upper()
        return bool(user and user.is_authenticated and role == 'TEACHER')


class IsTeacherOrReadOnly(BasePermission):
    """Leitura liberada para qualquer autenticado; escrita só para docentes/staff."""

    message = "Apenas docentes podem gerenciar banners."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_teacher(request.user)
