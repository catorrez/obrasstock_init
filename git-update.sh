#!/usr/bin/env bash
# Actualiza el repo actual: add -> commit -> pull --rebase -> push
# Uso: git-update
set -euo pipefail

# 0) Verificaciones
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ No estás dentro de un repositorio Git."
  exit 1
fi

branch="$(git rev-parse --abbrev-ref HEAD || echo main)"

# Detecta remoto (prefiere 'origin')
if git remote get-url origin >/dev/null 2>&1; then
  remote="origin"
else
  remote="$(git remote | head -n1 || true)"
  if [ -z "${remote}" ]; then
    echo "❌ No hay remoto configurado. Ejemplo:"
    echo "   git remote add origin git@github.com:catorrez/obrasstock.git"
    exit
  fi
fi

echo "📦 Repo: $(git rev-parse --show-toplevel)"
echo "🌿 Rama: ${branch}"
echo "🔗 Remoto: ${remote}"

# 1) Muestra cambios
echo "— git status —"
git status --short

# 2) Mensaje de commit
read -rp "✏️  Mensaje de commit (enter para automático): " msg
if [ -z "${msg}" ]; then
  msg="update: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
fi

# 3) Stage + commit (si hay cambios)
git add -A
if git diff --cached --quiet; then
  echo "ℹ️  No hay cambios para commitear. Haré pull/push por si hay remoto."
else
  git commit -m "${msg}"
fi

# 4) Actualiza desde remoto (si hay upstream)
if git rev-parse --symbolic-full-name --abbrev-ref @'{u}' >/dev/null 2>&1; then
  echo "⬇️  git pull --rebase ${remote} ${branch}"
  git pull --rebase "${remote}" "${branch}" || true
else
  echo "ℹ️  Esta rama aún no tiene upstream; saltando pull."
fi

# 5) Push (con upstream si hace falta)
if git rev-parse --symbolic-full-name --abbrev-ref @'{u}' >/dev/null 2>&1; then
  echo "⬆️  git push ${remote} ${branch}"
  git push "${remote}" "${branch}"
else
  echo "⬆️  git push -u ${remote} ${branch}"
  git push -u "${remote}" "${branch}"
fi

echo "✅ Listo."
