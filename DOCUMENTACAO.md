# Documentação do Floor 13

Este documento descreve o comportamento implementado no repositório. As regras e quantidades de itens são configuradas por fase: não há uma exigência global de três itens essenciais e três bônus. Para uma apresentação rápida do projeto, consulte o [README](README.md).

## 1. Visão geral

Floor 13 é um jogo desktop 2D feito em Python com Pygame. O prédio é modelado como um grafo: vértices representam andares e arestas representam elevadores. O jogador percorre o grafo para explorar o prédio, coletar itens ou resolver um desafio de grafos.

A aplicação descobre os arquivos `.json` da pasta `levels/`, valida cada configuração e usa os dados válidos para montar o seletor e a progressão de fases. O projeto também inclui um editor visual que usa o mesmo carregador e validador.

## 2. Requisitos e execução

- Python 3.10 ou superior.
- Dependência: `pygame-ce` (veja `requirements.txt`).

No Windows, PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Para executar os testes:

```powershell
python -m unittest discover -s tests -v
```

O jogo inicia pelo `main.py`. A janela pode ser redimensionada; o conteúdo mantém a proporção da área lógica do jogo.

## 3. Fluxo de jogo e controles

No menu, **Continuar** inicia a próxima fase recomendada pela progressão. **Selecionar fases** abre o seletor; fases concluídas e a próxima fase da sequência ficam disponíveis. **Editor de fases** abre o editor visual.

Na tela de jogo, a interface apresenta o andar atual e os destinos conectados. Selecione um destino antes de viajar. Em fases de coleta, use **Coletar** no andar onde os itens estão; chegar à saída sem cumprir os requisitos não conclui a fase.

| Ação | Teclado | Mouse |
|---|---|---|
| Coletar os itens do andar atual | `E` | Botão **Coletar** |
| Percorrer os destinos disponíveis | `Tab`, `←`, `→`, `↑`, `↓` | Clique em um destino |
| Inverter a direção da seleção | `Shift+Tab`, `←` ou `↑` | — |
| Viajar para o destino selecionado | `Enter` | Botão **Viajar** |
| Reiniciar uma fase de desafio especial | `R` | — |
| Voltar ao menu durante uma fase | `M` ou `Esc` | Botão de menu |
| Continuar após o resultado | `Enter` | Botão de continuar |
| Rejogar após o resultado | `R` | Botão de rejogar |
| Escolher fase pelo número | Teclas `1` a `9` | Clique na fase |
| Percorrer a lista de fases | — | Roda do mouse |

No menu principal, `Enter` continua e `S` abre a seleção de fases. No seletor, `Backspace` volta ao menu. Os comandos indicados na interface também podem ser acionados pelos botões.

### Regras de coleta

- Itens `essential` são necessários para completar um desafio do tipo `collect_and_exit`.
- Itens `bonus` são opcionais.
- Itens do tipo `key` são itens essenciais que podem desbloquear conexões ou ser exigidos pela saída.
- Itens coletados não reaparecem na tentativa atual.
- Objetivos opcionais podem recompensar ações como visitar um andar, coletar todos os bônus ou voltar ao início.
- O tipo de desafio determina a condição de conclusão; nem todos os desafios usam itens.

## 4. Desafios de grafos

O registro em `challenge_registry.py` associa cada valor de `challenge.type` a uma fábrica de estado de jogo e a um identificador de conclusão.

| Tipo JSON | Regra |
|---|---|
| `collect_and_exit` | Colete os itens essenciais, satisfaça os requisitos de chave e alcance a saída. |
| `hamilton` | Visite cada vértice exatamente uma vez, começando no início e terminando no andar final configurado. |
| `economic` | Alcance o destino por uma rota de custo mínimo. O custo é a soma dos pesos das arestas. |
| `euler` | Percorra cada aresta exatamente uma vez, do início até a saída. |
| `final` | Alcance o destino e retorne ao andar configurado com o menor custo total de ida e volta. |

Os desafios `economic` e `final` usam Dijkstra e exigem pesos estritamente positivos. A validação de `euler` exige grafo conectado, sem laços, com início e fim nos dois vértices de grau ímpar e uma trilha que cubra as arestas uma vez cada. A validação `hamilton` verifica a existência de uma rota compatível com os extremos configurados.

Os algoritmos genéricos em `algorithms.py` são busca em largura (BFS), Dijkstra e verificação de conectividade. BFS minimiza a quantidade de arestas sem considerar os pesos; Dijkstra minimiza o custo ponderado.

## 5. Fases incluídas

Os números e identificadores são lidos dos arquivos JSON. O projeto inclui 13 fases; as fases 6 a 13 aumentam de 6 até 13 andares:

| Fase | Nome | Desafio |
|---:|---|---|
| 1 | Primeiro contato | Coleta e saída |
| 2 | Sem voltar atrás | Hamiltoniano |
| 3 | Elevador econômico | Menor custo |
| 4 | Inspeção completa | Euleriano |
| 5 | A saída | Ida e volta de menor custo |
| 6 | O andar esquecido | Coleta e saída — 6 andares |
| 7 | O labirinto das sombras | Coleta e saída com chaves — 7 andares |
| 8 | O caminho mais curto | Menor custo — 8 andares |
| 9 | Inspeção em circuito | Euleriano — 9 andares |
| 10 | Ida e volta pelo núcleo | Ida e volta de menor custo — 10 andares |
| 11 | Travessia dos onze andares | Hamiltoniano — 11 andares |
| 12 | A ala lacrada | Coleta e saída com chaves — 12 andares |
| 13 | O coração do prédio | Ida e volta de menor custo — 13 andares, 25 conexões |

As fases 6 a 13 formam uma progressão de tamanho e combinam coleta com chaves, caminhos hamiltonianos, caminhos de custo mínimo, trilhas eulerianas e rotas de ida e volta. A fase 13 usa o maior grafo do jogo: 13 andares, 25 conexões ponderadas, itens bônus e objetivos opcionais.

## 6. Arquitetura

### Aplicação e domínio

- `main.py`: inicializa Pygame, carrega as fases e conecta menus, estados de jogo, editor, pontuação e salvamento.
- `graph.py`: grafo genérico, não direcionado, com peso finito e não negativo por aresta.
- `algorithms.py`: BFS, Dijkstra e conectividade.
- `level.py`: tipos imutáveis para fase, item, objetivo e requisito de conexão.
- `game_state.py`: estado e regras da coleta e saída.
- `level_manager.py`: leitura, validação, descoberta e construção das fases JSON.
- `level_editor.py`: interface e edição visual das configurações.
- `challenge_registry.py`: registro e criação de estados de desafio.
- `hamilton_challenge.py` / `hamilton_game_state.py`: desafio hamiltoniano.
- `economic_challenge.py` / `economic_game_state.py`: desafio de menor custo.
- `euler_challenge.py` / `euler_game_state.py`: desafio euleriano.
- `final_challenge.py` / `final_game_state.py`: desafio de ida e volta.

### Sistemas e dados

- `systems/menu_manager.py`: navegação entre menu, seleção, jogo e resultado.
- `systems/progress_manager.py`: desbloqueio e conclusão de fases.
- `systems/score_manager.py`: pontuação por tentativa, itens, objetivos e conclusão.
- `systems/item_manager.py`: itens coletados, andares visitados e objetivos opcionais.
- `systems/save_manager.py`: persistência e normalização do progresso.
- `levels/`: configurações JSON carregadas pelo jogo.
- `data/progress.json`: progresso, resultados e pontuações locais.
- `assets/`: imagens usadas na interface.
- `tests/`: testes unitários e de integração dos sistemas e desafios.

### Descoberta e validação

`LevelManager.discover_levels()` examina arquivos JSON na pasta de fases, valida cada um e ordena os válidos por número e identificador. Arquivos inválidos são ignorados com diagnóstico de erro; grafos desconectados geram aviso. IDs e números de fase duplicados fazem os arquivos conflitantes serem rejeitados.

A validação verifica, entre outras coisas, a existência dos andares inicial e de saída, pesos e conexões, IDs e tipos de itens, chaves e requisitos, parâmetros específicos de cada desafio e a possibilidade de concluir a fase. Campos desconhecidos também são rejeitados: o formato é intencionalmente estrito.

## 7. Criar e editar fases

### Pelo editor visual

Abra **Editor de fases** no menu. O editor permite criar ou abrir uma fase, posicionar andares, criar e remover conexões, editar andares inicial e de saída, configurar itens e objetivos, selecionar tipo e parâmetros de desafio e validar, salvar ou exportar o JSON.

Uma fase só aparece no jogo quando o arquivo JSON está dentro da pasta configurada em `levels/` e passa pela validação. Depois de alterar os arquivos enquanto o jogo está aberto, reinicie-o para executar novamente a descoberta.

### Formato JSON

Um arquivo de fase é um objeto JSON com estes campos:

| Campo | Descrição |
|---|---|
| `id` | Identificador único em minúsculas, com números e hífens, por exemplo `phase-13`. |
| `number` | Número inteiro positivo e único da fase. |
| `name` | Nome exibido no jogo. |
| `graph.vertices` | Lista não vazia de andares inteiros, sem repetição. |
| `graph.edges` | Lista de conexões não direcionadas; formato `[andarA, andarB]` ou `[andarA, andarB, peso]`. |
| `start_floor`, `exit_floor` | Andares de início e saída, ambos presentes em `vertices`. |
| `items` | Itens opcionais; IDs únicos, andar existente, tipo `essential`, `bonus` ou `key`, pontuação inteira não negativa. |
| `exit_requirements` | Opcional; `keys` lista as chaves exigidas e `challenges` os desafios exigidos pela saída. |
| `connection_requirements` | Opcional; requisitos de chaves para arestas específicas. |
| `challenge` | Tipo do desafio e parâmetros próprios daquele tipo. |
| `optional_objectives` | Opcional; objetivos opcionais e recompensas. |
| `rewards.completion` | Opcional; pontuação inteira não negativa por concluir (padrão: `300`). |

Exemplo mínimo válido de fase de coleta com uma chave:

```json
{
  "id": "phase-13",
  "number": 13,
  "name": "Nova rota",
  "graph": {
    "vertices": [1, 2],
    "edges": [[1, 2]]
  },
  "start_floor": 1,
  "exit_floor": 2,
  "items": [
    {
      "id": "chave-saida",
      "name": "Chave da saída",
      "floor": 1,
      "type": "key",
      "score": 100
    }
  ],
  "exit_requirements": {
    "keys": ["chave-saida"],
    "challenges": []
  },
  "connection_requirements": [],
  "challenge": {
    "type": "collect_and_exit"
  },
  "optional_objectives": [],
  "rewards": {
    "completion": 300
  }
}
```

As arestas não especificadas têm peso `1`. Os pesos devem ser finitos e não negativos; desafios de menor custo exigem peso positivo. Cada conexão deve referenciar andares existentes e não pode ser duplicada.

#### Itens, chaves e requisitos

- `type: "essential"` cria um item obrigatório; `type: "bonus"` cria um bônus; `type: "key"` cria um item obrigatório que também é chave.
- O campo opcional `key: true` também marca um item essencial como chave. Bônus não podem ser chaves.
- Itens bônus não podem compartilhar andar com itens essenciais.
- `exit_requirements.keys` deve listar IDs existentes de itens-chave.
- Um requisito de conexão segue o formato `{"from": 1, "to": 2, "keys": ["id-da-chave"]}`. A conexão deve existir no grafo.

#### Tipos de desafio e parâmetros

`challenge.type` aceita os cinco valores abaixo. Os parâmetros identificam vértices existentes:

- `collect_and_exit`: sem parâmetros adicionais.
- `hamilton`: `end_floor` opcional (padrão: andar de saída).
- `economic`: `destination_floor` opcional (padrão: andar de saída).
- `euler`: `reference_trail` obrigatória; sequência que começa no início e termina na saída, percorrendo cada conexão exatamente uma vez.
- `final`: `destination_floor` e `return_floor` opcionais (padrões: saída e início).

Os identificadores aceitos em `exit_requirements.challenges` correspondem ao tipo configurado: `collect_and_exit`, `hamilton`, `economic_optimal_route`, `euler_trail` ou `minimum_round_trip`.

#### Objetivos opcionais

Cada objetivo contém `id`, `name`, `description`, `type` e `reward`. Tipos aceitos:

- `visit_floor`: exige também `floor`, um vértice existente.
- `collect_all_bonus`: conclui ao coletar todos os itens bônus da fase.
- `return_to_start`: conclui ao retornar ao andar inicial depois de se deslocar.

## 8. Pontuação, progressão e salvamento

A pontuação de uma tentativa soma os pontos dos itens, as recompensas dos objetivos opcionais concluídos e a recompensa de conclusão do desafio. IDs repetidos não geram recompensa duplicada. O resultado também registra itens coletados, desafios e objetivos concluídos, deslocamentos e tempo decorrido.

O progresso mantém fases concluídas e desbloqueadas, pontuação por fase, melhor e último resultado e pontuação total. A próxima fase ainda não concluída é a recomendada; completar uma fase desbloqueia a próxima na ordem numérica.

O arquivo padrão é `data/progress.json`. O salvamento escreve primeiro em arquivo temporário e substitui o arquivo final atomicamente. Versões antigas do progresso são normalizadas; se um arquivo inválido for encontrado, ele é preservado com sufixo `.invalid-<data>` antes de iniciar um progresso padrão.

## 9. Testes e manutenção

Execute toda a suíte com:

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem algoritmos de grafos, navegação e controles, descoberta dinâmica e validação JSON das fases, editor, estados de jogo, desafios, pontuação, progressão e persistência.

Ao adicionar uma fase, confira o ID e o número únicos, valide todos os andares referenciados e confirme que existe uma rota de conclusão. Para desafios ponderados, use pesos positivos; para uma fase Euleriana, assegure conectividade e exatamente dois vértices de grau ímpar, correspondentes ao início e fim.
