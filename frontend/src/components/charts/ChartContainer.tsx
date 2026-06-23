import { lazy, Suspense } from "react";

// ReactECharts lazy laden -> eigener Chunk, schlankes Grund-Bundle (Spec §5).
const ReactECharts = lazy(() => import("echarts-for-react"));

export function ChartContainer({ option, height = 280 }: { option: object; height?: number }) {
  return (
    <Suspense fallback={<div className="text-sm text-slate-500">Diagramm lädt …</div>}>
      <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />
    </Suspense>
  );
}
