# Floor 13

Jogo 2D de exploração feito em Python e Pygame, no qual cada andar de um prédio é um vértice e cada elevador é uma aresta de um grafo. Explore conexões, cumpra desafios de teoria dos grafos e encontre a saída.

> **Conteúdo:** 13 fases JSON carregadas automaticamente. As fases 6 a 13 aumentam progressivamente de 6 a 13 andares; a fase 13 é a mais complexa, com 13 andares e 25 conexões.

## Funcionalidades

- Exploração de fases definidas como grafos não direcionados, com conexões ponderadas.
- Desafios de coleta e saída, caminho hamiltoniano, menor custo, trilha euleriana e ida e retorno de custo mínimo.
- Progressão de desafios e grafos crescentes: as fases 6–13 variam de 6 a 13 andares.
- Itens essenciais, bônus, chaves e objetivos opcionais.
- Editor visual para criar, alterar, validar e exportar fases.
- Progressão, pontuações e melhores resultados salvos em JSON.
- Testes automatizados para regras, algoritmos, interface e dados de fases.

## Requisitos

- Python 3.10 ou superior.
- Windows, macOS ou Linux com suporte a Pygame.

## Instalação e execução

No terminal, a partir da pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

O arquivo `requirements.txt` instala `pygame-ce`, que é importado pelo código como `pygame`.

## Como jogar

Escolha **Continuar** para abrir a próxima fase disponível ou **Selecionar fases** para escolher uma fase desbloqueada. No jogo, selecione um andar conectado e viaje até ele. Colete itens quando estiver no mesmo andar.

| Ação | Controle |
|---|---|
| Coletar itens | `E` ou botão **Coletar** |
| Escolher o próximo destino | Clique em um andar, use as setas ou `Tab` |
| Viajar | `Enter` ou botão **Viajar** |
| Reiniciar um desafio especial | `R` |
| Voltar ao menu | `M` ou `Esc` |
| Avançar após um resultado | `Enter` |
| Rejogar após um resultado | `R` |

As opções visíveis na tela também podem ser acionadas com o mouse. No seletor, a roda do mouse percorre a lista de fases.

## Testes

```powershell
python -m unittest discover -s tests -v
```

## Documentação

A [documentação completa do projeto](DOCUMENTACAO.md) detalha arquitetura, regras, desafios, fases, formato JSON, editor, persistência e testes.

## Estrutura do repositório

- `main.py`: aplicação e interface Pygame.
- `levels/`: arquivos JSON das fases.
- `graph.py`, `algorithms.py`: estrutura de grafo e algoritmos.
- `*_challenge.py`, `*_game_state.py`: regras dos desafios.
- `systems/`: menu, progressão, pontuação, itens e salvamento.
- `level_editor.py`: editor visual de fases.
- `tests/`: testes automatizados.
- `assets/`: recursos visuais.
