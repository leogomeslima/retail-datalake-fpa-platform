import { formatCompetence, formatCurrency, formatNumber, formatPercent } from "../utils/format";

const WIDTH = 920;
const HEIGHT = 330;
const PADDING = { top: 30, right: 22, bottom: 48, left: 74 };
const COLORS = ["#066b56", "#235d9f", "#b56813", "#7654b8", "#ba3f53"];

function valueLabel(value, type) {
  if (type === "currency") return formatCurrency(value);
  if (type === "percent") return formatPercent(value);
  return formatNumber(value);
}

export function LineChart({ series, valueKey, valueType, ariaLabel }) {
  const values = series.flatMap((line) => line.points.map((point) => Number(point[valueKey] || 0)));
  const periods = [...new Set(
    series.flatMap((line) => line.points.map((point) => point.competencia)),
  )].sort();
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const innerWidth = WIDTH - PADDING.left - PADDING.right;
  const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;

  function x(index) {
    return PADDING.left + (periods.length < 2 ? innerWidth / 2 : (index / (periods.length - 1)) * innerWidth);
  }

  function y(value) {
    return PADDING.top + ((max - Number(value || 0)) / range) * innerHeight;
  }

  const ticks = Array.from({ length: 5 }, (_, index) => max - (range / 4) * index);

  return (
    <div className="line-chart">
      <svg aria-label={ariaLabel} role="img" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className="chart-grid" x1={PADDING.left} x2={WIDTH - PADDING.right} y1={y(tick)} y2={y(tick)} />
            <text className="chart-axis" x={PADDING.left - 10} y={y(tick) + 4} textAnchor="end">
              {valueLabel(tick, valueType)}
            </text>
          </g>
        ))}
        {periods.map((competence, index) => (
          <text className="chart-axis" key={competence} textAnchor="middle" x={x(index)} y={HEIGHT - 16}>
            {formatCompetence(competence).replace(" de ", "/")}
          </text>
        ))}
        {series.map((line, lineIndex) => {
          const color = COLORS[lineIndex % COLORS.length];
          const points = line.points
            .map((point) => `${x(periods.indexOf(point.competencia))},${y(point[valueKey])}`)
            .join(" ");
          return (
            <g key={line.label}>
              <polyline className="chart-line" points={points} style={{ stroke: color }} />
              {line.points.map((point) => (
                <circle
                  className="chart-point"
                  cx={x(periods.indexOf(point.competencia))}
                  cy={y(point[valueKey])}
                  fill={color}
                  key={`${line.label}-${point.competencia}`}
                  r="4.5"
                >
                  <title>{`${line.label} - ${formatCompetence(point.competencia)}: ${valueLabel(point[valueKey], valueType)}`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>
      <div className="chart-legend">
        {series.map((line, index) => (
          <span key={line.label}>
            <i style={{ backgroundColor: COLORS[index % COLORS.length] }} />
            {line.label}
          </span>
        ))}
      </div>
    </div>
  );
}
