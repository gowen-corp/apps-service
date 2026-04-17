#!/bin/bash
# scripts/generate-report.sh
PERIOD="${1:-2 weeks ago}"
OUTPUT="${2:-report.md}"

cat > "$OUTPUT" <<EOF
# Отчёт: $(date +%Y-%m-%d) | Период: $PERIOD

## 🔢 Цифры
- Коммиты: $(git rev-list --count HEAD "$PERIOD")
- Файлов изменено: $(git diff --name-only HEAD "$PERIOD" | wc -l)
- AI-запросов: $(jq -r '.model' ~/.qwen/logs/*.jsonl 2>/dev/null | wc -l)

## 🚀 Сделано
$(git log --since="$PERIOD" --pretty=format:"- %s" --author="$(git config user.name)")

## 📁 Новые файлы
$(git diff --name-status HEAD "$PERIOD" | grep "^A" | cut -f2 | sed 's/^/- /')
EOF

echo "Готово: $OUTPUT"
