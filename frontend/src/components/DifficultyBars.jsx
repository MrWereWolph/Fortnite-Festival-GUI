const MAX_BLOCKS = 7;

function normalizeDifficulty(value) {
  if (value === null || value === undefined) return null;

  const numberValue = Number(value);

  if (!Number.isFinite(numberValue)) return null;

  // 99 should already be converted to null by the database view,
  // but this keeps the component safe.
  if (numberValue === 99) return null;

  return Math.min(MAX_BLOCKS, Math.max(1, numberValue));
}

export default function DifficultyBars({ label, value }) {
  const normalizedValue = normalizeDifficulty(value);
  const unavailable = normalizedValue === null;

  return (
    <div className={`difficulty-row ${unavailable ? "difficulty-row-na" : ""}`}>
      <div className="difficulty-label">{label}</div>

      <div className="difficulty-bars" aria-label={`${label} difficulty`}>
        {Array.from({ length: MAX_BLOCKS }).map((_, index) => {
          const filled = !unavailable && index < normalizedValue;

          return (
            <span
              key={index}
              className={`difficulty-block ${filled ? "filled" : ""}`}
            />
          );
        })}
      </div>

      <div className="difficulty-value">
        {unavailable ? "N/A" : normalizedValue}
      </div>
    </div>
  );
}