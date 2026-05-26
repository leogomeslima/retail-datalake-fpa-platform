export function LoadingState() {
  return (
    <main className="feedback">
      <div className="loader" />
      <h2>Carregando indicadores do Data Warehouse</h2>
      <p>Aguardando a leitura mais recente do pipeline.</p>
    </main>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <main className="feedback error-state">
      <h2>Dados indisponíveis</h2>
      <p>{message}</p>
      <button type="button" onClick={onRetry}>
        Tentar novamente
      </button>
    </main>
  );
}

