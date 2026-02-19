# Protocolo de Pesquisa de Edge (WDOFUT)

Objetivo: transformar análise exploratória em pesquisa reproduzível de edge, com foco em causalidade, validação fora da amostra e robustez.

## 1. Princípios

- Não adivinhar parâmetros críticos.
- Não usar informação futura (zero leakage).
- Não aceitar edge sem superar baselines.
- Não promover estratégia sem robustez OOS.
- Registrar tudo (inputs, métricas, veredito).

## 2. Research Contract (preencher antes de rodar)

Copie e preencha este bloco:

```yaml
dataset:
  ticker: WDOFUT_F_0
  period_start: YYYY-MM-DD
  period_end: YYYY-MM-DD
  session_filter: "ex.: 09:00-18:00 BRT"

label:
  horizon: "ex.: 5 ticks / 10s / 3 barras"
  target_type: "direção | retorno | evento"
  target_formula: ""
  timestamp_alignment: ""

execution:
  side: "long/short/flat"
  order_type: "market | limit"
  latency_model: ""
  max_position: 1
  sizing: "fixed 1-lot"

costs:
  spread_model: ""
  slippage_model: ""
  fees_model: ""
  total_cost_formula: ""

validation:
  split: "temporal"
  walk_forward: true
  train_ratio: 0.6
  val_ratio: 0.2
  test_ratio: 0.2

metrics:
  primary: ["net_pnl", "sharpe", "profit_factor", "max_drawdown", "hit_rate", "turnover"]
  minimum_samples: 100

kill_switch:
  min_oos_sharpe: 0.0
  min_profit_factor: 1.05
  max_drawdown_limit: ""
  min_trades_oos: 50
```

## 3. Sequência de execução no agente (prompts)

## Etapa 0 — Contrato

```text
Antes de qualquer análise, gere o Research Contract com todos os campos obrigatórios e marque PENDENTE o que faltar. Não continue sem esses campos definidos.
```

## Etapa 1 — Auditoria do dataset

```text
Liste arquivos/partições, linhas por dia, schema, nulos, duplicatas por timestamp, min/max timestamp por dia e estatísticas básicas de spread/mid/log_return. Sem gráficos.
```

## Etapa 2 — Definição de alvo sem leakage

```text
Proponha 2-3 definições causais de alvo y (com fórmula explícita, alinhamento temporal e prevenção de leakage). Não compute ainda.
```

Após escolher uma:

```text
Implemente o label escolhido com horizonte H definido no contract. Mostre distribuição, %zeros, assimetria e 5 exemplos com timestamp/preço/y.
```

## Etapa 3 — Baselines obrigatórios

```text
Rode baselines out-of-sample temporal:
1) no-trade
2) retorno passado simples
3) regra simples de spread/volatilidade
Com custos do contract. Reporte métricas primárias e compare.
```

## Etapa 4 — Feature set causal

```text
Gere feature set v1 totalmente causal (retornos/volatilidade, reversão/tendência, regimes, custo/liquidez). Para cada feature: fórmula, janela, custo computacional. Depois reporte análise univariada com y.
```

## Etapa 5 — Hipóteses de edge (rule-based)

```text
Proponha 10 hipóteses de edge microestrutural com:
- entrada
- saída
- racional
- regime esperado
Selecione as 3 mais plausíveis e implemente backtests rule-based.
```

## Etapa 6 — Walk-forward com custos

```text
Execute backtest event-driven com custos e restrições do contract.
Rode walk-forward temporal (train/val/test).
Entregue métricas agregadas + por janela + por dia/turno.
```

## Etapa 7 — Robustez (anti-edge falso)

```text
Para a melhor estratégia:
- sensibilidade de parâmetros (grid curto)
- estabilidade por dia/turno/regime
- block bootstrap para IC de Sharpe/PnL
- placebo (embaralhar label e/ou inverter sinal)
Conclusão binária: robusta para continuar vs descartar.
```

## Etapa 8 — Relatório final

```text
Entregue:
- estratégia vencedora (se houver)
- ganho real sobre baselines
- regimes onde falha
- parâmetros estáveis
- próximos 5 experimentos priorizados
- riscos de execução real
```

## 4. Critérios de Go/No-Go

Go (seguir):
- supera baselines em OOS
- métricas líquidas positivas após custos
- estabilidade em múltiplas janelas/regimes
- placebo não reproduz resultado

No-Go (descartar):
- melhora só in-sample
- quebra em test window
- alta sensibilidade paramétrica
- performance explicada por poucos dias/eventos

## 5. Artefatos por experimento

Salvar em `experiments/<timestamp>_<slug>/`:

- `contract.json` (parâmetros fixos do estudo)
- `features.md` (definições)
- `metrics.json` (IS/OOS + por janela)
- `robustness.json` (sensibilidade/bootstrap/placebo)
- `verdict.md` (go/no-go + justificativa)

## 6. Template de veredito

```md
# Verdict

- Experiment: <id>
- Decision: GO | NO-GO
- Why:
  - baseline comparison:
  - OOS performance:
  - robustness tests:
  - execution risk:
- Next action:
```

