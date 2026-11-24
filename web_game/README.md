# Floor 13 — versão web

Esta pasta contém a interface web do jogo original. O navegador não executa as regras do grafo: ele conversa com `server.py`, que reutiliza os módulos Python do projeto. A versão Pygame não é alterada.

## Executar

Na raiz do projeto, execute:

```powershell
py web_game/server.py
```

Depois abra `http://127.0.0.1:4173`. O servidor carrega as fases de `levels/` usando `LevelManager`.

## Conteúdo

- `index.html`: menu, seleção de fases, jogo, editor e painel de algoritmos.
- `styles.css`: interface escura com cenário em pixel art construído em CSS.
- `server.py`: API HTTP, sessões de jogo, validação e chamadas aos algoritmos Python.
- `app.js`: renderização, controles, chamadas à API e estado visual.
- `levels-data.js`: dados estáticos antigos mantidos como referência; não é carregado pela interface atual.

## Regras preservadas

- Cada andar é um vértice do grafo.
- Cada aresta incidente ao andar vira exatamente um elevador visível naquele andar.
- Um elevador só oferece o outro extremo da própria aresta.
- A conectividade, Dijkstra, Hamiltoniano e Euleriano são executados pelos módulos Python originais.
- Fases criadas pelo editor são validadas e salvas em `web_game/custom_levels.json` pelo backend.
- O personagem se move somente para a esquerda e para a direita dentro do piso.
- Cada andar possui um piso pixelado visível; cada cabine mostra seu destino acima da imagem.
