import { formatCompetence } from "../utils/format";

export function Filters({ competences, selected, onSelect, onRefresh }) {
  return (
    <section className="filters" aria-label="Filtros do painel">
      <div>
        <label htmlFor="competence">Competência analisada</label>
        <select id="competence" value={selected || "sem-dados"} onChange={(event) => onSelect(event.target.value)}>
          {competences.map((competence) => (
            <option value={competence} key={competence}>
              {formatCompetence(competence)}
            </option>
          ))}
        </select>
      </div>
      <p>
        Atualização automática a cada <strong>15 segundos</strong>
      </p>
      <button type="button" onClick={onRefresh}>
        Atualizar agora
      </button>
    </section>
  );
}
