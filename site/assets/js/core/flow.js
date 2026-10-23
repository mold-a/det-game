// Порядок вопросов этапа (docs/01 «Поток этапа»): вопросы идут по одному, следующий
// появляется после ответа на текущий. Логика без DOM; порядок выводится из прогресса
// (units[path]: solved / closed), отдельного поля в сохранении нет — старые сохранения работают.
// Тесты — tests/js/flow.test.mjs.

const isMandatory = (q) => q.kind === "mandatory";
const isBonus = (q) => q.kind === "bonus";
const solved = (units, q) => units?.[q.path]?.status === "solved";
const answered = (units, q) => Boolean(units?.[q.path]);

/**
 * Какие вопросы этапа видны.
 *   pack  — { questions: [{ path, kind: "mandatory" | "bonus" | "final" }] } в порядке контента;
 *   units — прогресс `state.units`.
 * → {
 *   mandatory: { shown, hidden },  — решённые + первый нерешённый; hidden — сколько ещё скрыто;
 *   bonus:     { shown, hidden },  — отвеченные + первый неотвеченный (только когда решены все обязательные);
 *   current,                       — путь вопроса, на который сейчас отвечает команда, или null;
 *   complete,                      — все обязательные решены.
 * }
 * Обязательные: следующий появляется после верного ответа на предыдущий. Бонусы идут после последнего
 * обязательного; следующий — после ответа на предыдущий, верного или нет (одна попытка).
 * Скрытые вопросы не показываются вовсе (ни заголовком, ни числом в тексте — только счётчик для строки-заглушки).
 * Старые сохранения, где вопросы решались в любом порядке: решённые и отвеченные видны всегда.
 */
export function stageFlow(pack, units) {
  const qs = pack?.questions ?? [];
  const mand = qs.filter(isMandatory);
  const bons = qs.filter(isBonus);

  const firstOpen = mand.find((q) => !solved(units, q));
  const mShown = mand.filter((q) => solved(units, q) || q === firstOpen);
  const complete = !firstOpen;

  const firstBonus = complete ? bons.find((q) => !answered(units, q)) : undefined;
  const bShown = bons.filter((q) => answered(units, q) || q === firstBonus);

  return {
    mandatory: { shown: mShown, hidden: mand.length - mShown.length },
    bonus: { shown: bShown, hidden: bons.length - bShown.length },
    current: firstOpen?.path ?? firstBonus?.path ?? null,
    complete,
  };
}

/** Бонусы этапа, на которые ещё не отвечали (и ещё можно ответить: финал не начат). */
export function pendingBonuses(pack, state) {
  if (!pack || state.final?.started || state.finished) return [];
  return (pack.questions ?? []).filter((q) => isBonus(q) && !state.units?.[q.path]);
}

/**
 * Какой этап показывает главный экран. Обычно текущий (`state.stage`). Но пока конверт нового этапа
 * не вскрыт (`envelopeAck < stage`), а у только что пройденного этапа есть неотвеченные бонусы, экран
 * остаётся на пройденном этапе: бонусы показываются до окна «Откройте конверт №N» — иначе они
 * потерялись бы за переходом. packs — { [n]: pack } (достаточно этапа stage − 1).
 */
export function viewStage(state, packs) {
  const n = state.stage;
  if (n > 1 && state.envelopeAck < n && pendingBonuses(packs?.[n - 1], state).length) return n - 1;
  return n;
}
