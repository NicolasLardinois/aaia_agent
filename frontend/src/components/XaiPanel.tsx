import { useState } from "react";

export interface XaiDriver { text: string; sign: "+" | "-"; }
export interface XaiContent {
  drivers: XaiDriver[];
  conflicts: string[];
  confidenceReason: string;
  whatFlips: string;
}

// Aufklappbares XAI-Panel (Konzept §4.6): die vier Fragen — Treiber (+/-),
// Widersprueche, warum diese Konfidenz, was kippt es.
export function XaiPanel({ xai }: { xai: XaiContent }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded border border-slate-200 dark:border-slate-700">
      <button type="button" onClick={() => setOpen((o) => !o)} className="w-full px-3 py-2 text-left text-sm font-medium">
        XAI — Begründung {open ? "▾" : "▸"}
      </button>
      {open && (
        <div className="space-y-2 px-3 pb-3 text-sm">
          <div>
            <div className="text-xs uppercase text-slate-500">Entscheidende Signale</div>
            <ul>
              {xai.drivers.map((d, i) => (
                <li key={i} className={d.sign === "+" ? "text-green-600" : "text-red-600"}>
                  {d.sign === "+" ? "＋" : "－"} {d.text}
                </li>
              ))}
            </ul>
          </div>
          <div><span className="text-xs uppercase text-slate-500">Widersprüche: </span>{xai.conflicts.join("; ") || "—"}</div>
          <div><span className="text-xs uppercase text-slate-500">Konfidenz-Begründung: </span>{xai.confidenceReason}</div>
          <div><span className="text-xs uppercase text-slate-500">Was es kippen würde: </span>{xai.whatFlips}</div>
        </div>
      )}
    </div>
  );
}
