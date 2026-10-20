import type { ConjugationAnalysis } from "./conjugation";

export function ConjugationExplanation({
  analysis,
}: {
  analysis: ConjugationAnalysis | null;
}) {
  if (!analysis) return null;
  return (
    <details className="popup-disclosure conjugation-explanation">
      <summary>
        Conjugation ·{" "}
        {analysis.status === "supported" ? analysis.label : "Not covered"}
      </summary>
      <div className="conjugation-content">
        <p lang="ja">{analysis.surface}</p>
        {analysis.status === "supported" ? (
          <>
            <ol>
              {analysis.steps.map((item, index) => (
                <li key={index}>
                  <p lang="ja">
                    {item.from} → {item.to}
                  </p>
                  <p>{item.explanation}</p>
                </li>
              ))}
            </ol>
            <p className="popup-metadata">
              {analysis.note ??
                "Possible analysis from local tokenization. Meaning and tense depend on context."}
            </p>
          </>
        ) : (
          <p className="popup-metadata">{analysis.reason}</p>
        )}
      </div>
    </details>
  );
}
