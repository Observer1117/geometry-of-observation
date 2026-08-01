# GO Core v0.2 — отчёт линтера по корпусу

Статус этого отчёта: машинный аудит типизированных ledgers. Для старых PDF использованы адаптеры критических формул; это не полное синтаксическое доказательство корректности каждой формулы.

## Сводка

- канонических документов: 4;
- полных эталонных ledgers: 4;
- адаптеров критических формул: 0;
- проверенных выражений: 39;
- всех находок: 0;
- статусы: `{'PASS': 4}`.

## Статусы документов

| Документ | Ledger | Выражения | Auto | Review | Ошибки | Блокеры | Статус |
|---|---:|---:|---:|---:|---:|---:|---:|
| `frames-forces-dissipation-interface-v0-1` | reference | 10 | 0 | 0 | 0 | 0 | **PASS** |
| `celestial-foucault-networks-v1-1` | reference | 7 | 0 | 0 | 0 | 0 | **PASS** |
| `bobsleigh-contact-v1-1` | reference | 11 | 0 | 0 | 0 | 0 | **PASS** |
| `roller-coaster-v1-1` | reference | 11 | 0 | 0 | 0 | 0 | **PASS** |

## Находки по правилам


## Детальная карта исправлений

### Frames, Forces, Constraints, and Dissipation under Observation Maps (0.1.0)

Статус: **PASS**. Следующее действие: retain_as_common_mechanics_reference

- Нарушений не найдено в заявленном покрытии.

### Foucault Networks on Celestial Bodies (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_frame_consistent_celestial_toy_reference

- Нарушений не найдено в заявленном покрытии.

### Bobsleigh Contact Geometry as a Typed Observation System (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_typed_contact_observation_reference

- Нарушений не найдено в заявленном покрытии.

### Roller-Coaster Geometry as a Typed Observation Laboratory (1.1.0)

Статус: **PASS**. Следующее действие: retain_as_framed_curve_observation_reference

- Нарушений не найдено в заявленном покрытии.

## Интерпретация шлюза

- `PASS` означает прохождение зарегистрированного P0/P1-контракта.
- `FAIL` означает обнаруженную формульную, типовую, кадровую или семантическую ошибку.
- `BLOCKED` означает, что критические примеры не дали ошибки, но покрытие старого PDF недостаточно для строгого P1-pass.
- `REVIEW` означает отсутствие ошибок и блокеров при наличии нефатальных замечаний.
