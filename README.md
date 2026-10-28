# DOCUMENTAÇÃO TÉCNICA DO PROJETO
## Floor 13 — Jogo de exploração baseado em teoria dos grafos

**Versão:** 1.0  
**Linguagem:** Python  
**Biblioteca gráfica:** Pygame  
**Plataforma:** Computador (desktop)  
**Escopo inicial:** Protótipo funcional com 5 fases  
**Objetivo acadêmico:** Aplicação prática de conceitos e algoritmos de teoria dos grafos estudados em Matemática Discreta II.

---

# 1. VISÃO GERAL DO PROJETO

Desenvolva um jogo 2D de exploração chamado **Floor 13**, utilizando Python e Pygame.

O jogador começa em um andar de um prédio misterioso e precisa explorar diferentes andares utilizando elevadores. Cada andar pode possuir elevadores que levam a outros andares específicos, itens colecionáveis e uma saída, dependendo da fase.

O jogador não conhece a estrutura completa do prédio no início. Ele deve descobrir progressivamente quais andares existem e quais conexões estão disponíveis, construindo mentalmente ou visualmente um mapa das áreas exploradas.

O objetivo principal é coletar três itens essenciais e alcançar a saída da fase. Além disso, existem três itens bônus, localizados em andares exclusivos e opcionais, que não são necessários para concluir a missão, mas contribuem para alcançar a pontuação máxima.

O jogo deve exigir planejamento de rotas, exploração, análise das conexões e otimização dos deslocamentos. A teoria dos grafos será utilizada internamente para representar o prédio, calcular rotas e validar as soluções do jogador, sem necessariamente ser apresentada como conteúdo matemático explícito durante a experiência.

A inspiração de design é o jogo *BattleBlock Theater*, principalmente pela ideia de coletáveis, progressão por fases e recompensas por completar objetivos opcionais. O projeto deve ter identidade visual própria.

## 1.1. Princípios fundamentais

- O prédio é representado internamente por um grafo.
- Cada vértice representa um andar.
- Cada aresta representa uma conexão de elevador entre dois andares.
- O mapa completo não deve ser revelado ao jogador no início.
- A exploração deve revelar progressivamente as conexões.
- Cada fase possui três itens essenciais e três itens bônus.
- Os três itens bônus devem estar em andares exclusivos, distintos dos andares que contêm os itens essenciais.
- Os itens bônus são totalmente opcionais e nunca podem ser necessários para concluir uma fase.
- O jogador deve conseguir concluir cada fase coletando somente os itens essenciais e alcançando a saída.
- A pontuação máxima exige a coleta dos seis itens, além do cumprimento das demais condições de pontuação.
- O número de deslocamentos deve ser registrado e utilizado na avaliação de eficiência da rota.
- As cinco fases devem ser previamente verificadas para garantir que sejam solucionáveis.

---

# 2. CONCEITO E OBJETIVO DO JOGO

O jogador acorda no primeiro andar de um prédio desconhecido. Ele precisa explorar o local, encontrar três objetos essenciais e descobrir como chegar à saída.

Os elevadores não conectam necessariamente todos os andares diretamente. Cada elevador permite chegar apenas aos andares definidos para aquela conexão.

Durante a exploração, o jogador encontra objetos, descobre novas conexões e decide quais andares visitar.

Os itens essenciais são obrigatórios para concluir a missão. Os itens bônus estão escondidos em andares opcionais e podem exigir desvios da rota principal.

O desafio consiste em equilibrar três fatores:

1. Explorar o prédio e descobrir suas conexões.
2. Coletar os itens essenciais e alcançar a saída utilizando uma rota válida e eficiente.
3. Decidir se vale a pena desviar da rota para coletar os itens bônus e obter a pontuação máxima.

O jogo deve permitir que o jogador conclua uma fase sem encontrar ou coletar todos os itens bônus.

## 2.1. Condição geral de vitória

Uma fase é concluída quando todas as condições abaixo forem satisfeitas:

- O jogador coletou os três itens essenciais.
- O jogador alcançou o andar de saída definido para a fase.
- Todas as regras específicas da fase foram respeitadas.

Os itens bônus não participam da condição de vitória.

Caso o jogador alcance a saída sem ter coletado os três itens essenciais, a fase não deve ser concluída. O jogo deve informar quais itens ainda faltam e permitir que o jogador continue explorando.

O jogador não deve ser obrigado a visitar todos os andares do prédio em todas as fases. Alguns andares podem ser necessários para obter os itens essenciais, enquanto outros podem ser completamente opcionais.

---

# 3. REPRESENTAÇÃO MATEMÁTICA DO PRÉDIO

A estrutura do prédio deve ser representada por um grafo.

Considere um grafo \(G=(V,E)\), em que:

- \(V\) é o conjunto de vértices, representando os andares.
- \(E\) é o conjunto de arestas, representando as conexões entre elevadores e andares.

Cada andar deve possuir um identificador único, como `1`, `2`, `3`, `4` etc.

Cada conexão deve informar os andares de origem e destino. Opcionalmente, poderá possuir um peso que represente o custo de deslocamento.

Na versão inicial, o jogo deve utilizar grafos não direcionados: se um elevador conecta o andar A ao andar B, a viagem entre esses andares é possível nos dois sentidos, salvo se uma fase especificar explicitamente uma regra diferente.

Quando não houver pesos diferentes entre as conexões, cada deslocamento por elevador terá custo unitário. Dessa forma, minimizar o custo da rota equivale a minimizar o número de deslocamentos.

## 3.1. Grafo real e grafo descoberto

O sistema deve manter duas representações separadas.

**Grafo real:** contém todos os andares, todas as conexões, a localização dos itens e a saída. Essa estrutura é utilizada pelo sistema para validar movimentos e calcular soluções.

**Grafo descoberto:** contém apenas os andares e as conexões que o jogador já descobriu. Essa estrutura é utilizada para apresentar as informações conhecidas pelo jogador.

O grafo real nunca deve ser apresentado integralmente ao jogador antes de ele descobrir as respectivas informações.

Ao entrar em um andar, o jogador deve descobrir os destinos dos elevadores disponíveis naquele andar. As conexões recém-descobertas devem ser registradas no mapa explorado.

O sistema não deve revelar automaticamente todos os andares que ainda não foram visitados, a menos que exista uma mecânica específica da fase que permita isso.

## 3.2. Representação dos andares

Cada andar deve conter, no mínimo:

- Identificador do andar.
- Lista de andares acessíveis por elevador.
- Estado de descoberta pelo jogador.
- Lista de itens presentes.
- Informação sobre a presença ou ausência da saída.
- Estado de visita do jogador.

Os itens devem ser objetos independentes associados aos andares.

---

# 4. ITENS COLECIONÁVEIS

Cada fase deve conter exatamente seis itens colecionáveis: três essenciais e três bônus.

## 4.1. Itens essenciais

Os itens essenciais são obrigatórios para concluir a fase.

Regras:

- Devem existir exatamente três itens essenciais em cada fase.
- Cada item essencial deve estar associado a um andar.
- Os três itens essenciais devem estar distribuídos em andares distintos.
- O sistema deve registrar quais itens já foram coletados.
- Um item coletado não deve reaparecer após o jogador retornar ao andar.
- O jogador deve poder retornar à saída somente depois de coletar os três itens essenciais, quando a saída for o ponto de conclusão da missão.

Os itens podem ser representados inicialmente por formas geométricas coloridas, letras ou símbolos simples, sem necessidade de imagens elaboradas.

## 4.2. Itens bônus

Os itens bônus são opcionais e existem para incentivar a exploração e aumentar a pontuação.

Regras obrigatórias:

- Devem existir exatamente três itens bônus por fase.
- Cada item bônus deve estar localizado em um andar exclusivo.
- Os três andares dos itens bônus devem ser distintos entre si.
- Nenhum andar que contenha um item bônus pode conter um item essencial.
- Os itens bônus não podem ser necessários para alcançar ou ativar a saída.
- A ausência de um item bônus nunca pode bloquear o progresso da missão.
- O jogador deve conseguir concluir a fase mesmo sem coletar nenhum item bônus.
- Os itens bônus devem contribuir para a pontuação final.

Os andares bônus podem estar em desvios da rota principal, mas devem ser acessíveis quando a fase exigir que o jogador tenha a possibilidade de coletá-los.

O jogo não deve obrigar o jogador a visitar todos os vértices apenas porque existem itens bônus em outros andares.

## 4.3. Estado dos itens

Cada item deve possuir um identificador único, um tipo (`essencial` ou `bonus`), um andar de localização e um estado de coleta.

Quando o jogador entrar em um andar com um item disponível, o item poderá ser coletado automaticamente ou por meio de uma interação simples. Para a primeira versão, prefira coleta automática ao entrar no andar.

O sistema deve atualizar imediatamente o contador de itens essenciais e bônus.

---

# 5. EXPLORAÇÃO E MOVIMENTAÇÃO

A interface inicial não precisa ser sofisticada. A prioridade é garantir que o jogo seja funcional e que as regras estejam corretas.

O jogador deve conseguir:

- Visualizar o andar atual.
- Ver os elevadores disponíveis naquele andar.
- Escolher um destino entre os elevadores conhecidos.
- Viajar para o andar escolhido.
- Coletar itens ao entrar em um andar.
- Consultar os itens já coletados.
- Consultar a saída da fase, quando descoberta.
- Visualizar o mapa parcial, caso o sistema de mapa seja implementado na primeira versão.

## 5.1. Sistema de exploração

A exploração deve revelar informações progressivamente.

Ao iniciar uma fase, o jogador conhece apenas o andar inicial e as conexões que podem ser observadas nele.

Ao visitar um novo andar, o jogo revela as conexões desse andar e atualiza o registro de exploração.

O sistema deve permitir que o jogador retorne a andares anteriormente visitados.

A descoberta de um andar e a visita a um andar devem ser tratadas como estados diferentes: um andar pode ser conhecido por estar conectado a um elevador já descoberto, mesmo que o jogador ainda não tenha entrado nele.

## 5.2. Interface inicial

Utilize uma interface simples em Pygame, com formas geométricas e texto.

A tela principal da fase deve mostrar:

- Número ou nome da fase.
- Número do andar atual.
- Lista de destinos disponíveis.
- Quantidade de itens essenciais coletados.
- Quantidade de itens bônus coletados.
- Número de deslocamentos realizados.
- Mensagens de orientação ou de erro.
- Indicação da saída, quando essa informação estiver disponível ao jogador.

A apresentação visual dos andares pode ser uma tela de elevador com botões numerados. Não é necessário implementar movimentação física de um personagem pelos corredores na primeira versão.

A estrutura deve permitir adicionar posteriormente um personagem, animações e cenários mais elaborados sem alterar a lógica dos grafos.

---

# 6. REGRAS DE DESLOCAMENTO E OTIMIZAÇÃO

Cada viagem de um andar a outro por uma conexão válida de elevador deve contar como um deslocamento.

Por exemplo, sair do andar 1 para o andar 3 representa um deslocamento. Voltar do andar 3 para o andar 1 representa outro deslocamento.

Na primeira versão, o sistema deve minimizar o número total de deslocamentos. Todos os elevadores terão custo unitário, a menos que a fase especifique pesos diferentes.

O número de deslocamentos deve ser registrado durante toda a fase, incluindo os retornos a andares já visitados.

O jogador não deve receber automaticamente a solução ótima antes de tentar resolver a fase. O sistema poderá calcular a solução ótima internamente para verificar o resultado e determinar a pontuação.

## 6.1. Definição da rota ótima

A rota ótima de uma fase deve ser definida considerando:

- Andar inicial.
- Andar de saída.
- Três itens essenciais obrigatórios.
- Conexões disponíveis.
- Possibilidade de revisitar andares.
- Restrições específicas da fase.

A rota mínima deve incluir todos os deslocamentos necessários para coletar os itens essenciais e alcançar a saída.

Não se deve calcular a rota ótima considerando apenas a distância entre o andar inicial e a saída, ignorando os itens.

A coleta dos itens bônus deve ser tratada como uma otimização secundária: a rota que coleta os seis itens pode ser mais longa do que a rota mínima que coleta somente os itens essenciais.

A pontuação deve considerar essas duas possibilidades separadamente.

---

# 7. APLICAÇÃO DA TEORIA DOS GRAFOS

A teoria dos grafos deve ser utilizada de forma funcional. O jogador deve precisar planejar suas decisões, mas não é necessário apresentar equações ou nomes de algoritmos na interface durante a partida.

## 7.1. Conectividade e exploração

Utilizar a representação do grafo para determinar quais andares são alcançáveis a partir do andar atual.

O sistema deve identificar se um item ou a saída está em uma região inacessível a partir do início. Nenhuma fase poderá exigir um objetivo que não seja alcançável pelas regras estabelecidas.

## 7.2. Dijkstra

Implementar o algoritmo de Dijkstra para calcular os menores caminhos entre andares quando as conexões possuem pesos não negativos.

Na primeira versão, com pesos unitários, o resultado será equivalente ao obtido por uma busca em largura (BFS). Ainda assim, Dijkstra deverá ser implementado e testado para demonstrar sua aplicação acadêmica.

Quando a fase exigir a coleta de vários itens, não utilizar apenas o menor caminho entre a origem e a saída. Será necessário considerar a ordem de visita aos itens obrigatórios.

## 7.3. Caminho hamiltoniano

O conceito de caminho hamiltoniano poderá ser utilizado em uma fase específica na qual o jogador precise visitar cada andar exigido exatamente uma vez.

Essa regra não deve ser aplicada automaticamente a todas as fases.

Caso uma fase imponha a restrição de não repetir andares, ela deverá possuir uma rota válida que satisfaça a condição e que também permita coletar os três itens essenciais e alcançar o destino definido.

A presença de itens bônus em andares opcionais não deve obrigar o jogador a visitar esses andares.

## 7.4. Caminho de Euler

O conceito de caminho de Euler poderá ser utilizado em uma fase específica na qual o objetivo seja percorrer todas as conexões de elevador exatamente uma vez.

Essa fase deve possuir uma configuração de grafo compatível com a existência de um caminho de Euler, caso o objetivo seja obrigatório.

Não confundir a exigência de visitar todos os andares com a exigência de percorrer todas as conexões. São problemas matemáticos diferentes.

## 7.5. Prim e Kruskal

Prim e Kruskal não precisam fazer parte das cinco fases iniciais, pois o foco principal será explorar o prédio e coletar itens.

Entretanto, o código deve ser organizado de modo que esses algoritmos possam ser adicionados posteriormente para uma missão de reconstrução da rede de elevadores com custo mínimo.

---

# 8. PLANEJAMENTO DAS CINCO FASES

O jogo deve possuir cinco fases de apresentação, com dificuldade progressiva.

Cada fase deve possuir um grafo previamente definido e validado, com um início, uma saída, três itens essenciais e três itens bônus.

## Fase 1 — Primeiro contato

**Objetivo:** apresentar a exploração e o funcionamento dos elevadores.

- Aproximadamente 5 andares.
- Início no primeiro andar.
- Três itens essenciais em andares distintos.
- Três itens bônus em outros três andares exclusivos.
- Saída em um andar definido.
- Conexões simples, com mais de uma possibilidade de deslocamento.

O jogador deve aprender a descobrir conexões, reconhecer andares já visitados e retornar quando necessário.

**Conceito principal:** vértices, arestas, adjacência e conectividade.

## Fase 2 — Sem voltar atrás

**Objetivo:** introduzir um desafio baseado em caminho hamiltoniano.

- Aproximadamente 6 andares.
- Rota principal planejada para permitir a visita de todos os andares obrigatórios sem repetição.
- Três itens essenciais em andares distintos.
- Três itens bônus em andares exclusivos e opcionais.
- Saída em um andar definido.

A fase deve possuir ao menos uma rota válida que cumpra as restrições de visita e permita concluir a missão.

**Conceito principal:** caminho hamiltoniano.

## Fase 3 — O elevador econômico

**Objetivo:** exigir planejamento da rota com o menor número de deslocamentos.

- Aproximadamente 7 andares.
- Três itens essenciais em andares distintos.
- Três itens bônus em andares exclusivos e opcionais.
- Possibilidade de retornar a andares já visitados.
- Saída definida, que pode ser diferente do início.

O jogador deverá encontrar uma rota que passe pelos três itens essenciais e alcance a saída com o menor número de deslocamentos possível.

**Conceito principal:** caminho mínimo, Dijkstra e planejamento da ordem de coleta.

## Fase 4 — Inspeção completa

**Objetivo:** introduzir o desafio de percorrer todas as conexões de elevador exatamente uma vez.

- Aproximadamente 7 andares.
- Grafo projetado para permitir um caminho de Euler válido.
- Três itens essenciais em andares distintos.
- Três itens bônus em andares exclusivos e opcionais.
- Saída compatível com as condições do percurso.

A coleta dos itens essenciais deve ser possível sem exigir que os itens bônus sejam coletados.

**Conceito principal:** caminho ou circuito de Euler.

A fase deve deixar claro que o jogador está tentando percorrer todas as conexões, e não simplesmente visitar todos os andares.

## Fase 5 — A saída

**Objetivo:** combinar exploração, coleta de itens e otimização de deslocamentos.

- Aproximadamente 8 andares.
- Início no primeiro andar.
- Saída no primeiro andar ou em outro andar definido pela missão.
- Três itens essenciais em andares distintos.
- Três itens bônus em andares exclusivos e opcionais.
- Mapa parcialmente desconhecido no início.
- Conexões distribuídas de forma a exigir planejamento.

O jogador deve explorar, reunir os itens essenciais e encontrar a rota de menor custo para concluir a missão. A coleta dos bônus poderá exigir desvios e um percurso mais longo.

**Conceitos principais:** exploração de grafos, caminhos mínimos e otimização de rota.

A dificuldade deve resultar da configuração das conexões e da distribuição dos itens, e não de uma quantidade excessiva de andares.

---

# 9. SISTEMA DE PONTUAÇÃO

Cada fase deve permitir obter até 1.000 pontos.

Distribuição proposta:

- 500 pontos por concluir a fase com os três itens essenciais.
- 300 pontos pela coleta dos três itens bônus.
- 200 pontos por completar a missão utilizando a quantidade mínima possível de deslocamentos para os objetivos efetivamente cumpridos.

A pontuação deve ser calculada ao concluir a fase.

A pontuação pela rota ótima deve ser avaliada de acordo com os objetivos cumpridos. Se o jogador não coletar os itens bônus, a comparação deve considerar a rota ótima para coletar os itens essenciais e alcançar a saída, sem exigir os bônus.

Se o jogador coletar os três bônus, o jogo deverá considerar o menor percurso possível que inclua os seis itens e a saída.

A implementação poderá distribuir proporcionalmente os 200 pontos de eficiência conforme a diferença entre os deslocamentos realizados e a rota ótima correspondente.

A pontuação não deve impedir a conclusão da fase. O jogador pode terminar a missão com uma pontuação inferior à máxima.

O sistema deve registrar a pontuação de cada fase e permitir que o jogador tente novamente para melhorar o resultado.

---

# 10. ARQUITETURA DO PROJETO

Utilize Python e Pygame. Mantenha a lógica matemática separada da apresentação gráfica.

Estrutura inicial recomendada:

```text
floor13/
├── main.py
├── graph.py
├── algorithms.py
├── player.py
├── game_controller.py
├── level_manager.py
├── score_manager.py
├── ui.py
├── levels/
│   ├── level_1.json
│   ├── level_2.json
│   ├── level_3.json
│   ├── level_4.json
│   └── level_5.json
└── assets/
    └── images/
```

## 10.1. main.py

Responsável por inicializar o Pygame, criar a janela, controlar o ciclo principal do jogo, processar eventos e atualizar a tela.

## 10.2. graph.py

Responsável por representar o prédio como um grafo.

Deve conter:

- Vértices e identificadores dos andares.
- Lista de adjacência.
- Arestas e respectivos pesos.
- Grafo real.
- Grafo descoberto.
- Registro de andares conhecidos e visitados.
- Funções para consultar conexões disponíveis.

## 10.3. algorithms.py

Responsável pela implementação dos algoritmos e verificações matemáticas.

Deve incluir:

- Dijkstra.
- Busca em largura (BFS).
- Verificação de conectividade.
- Verificação de caminhos hamiltonianos para as fases pertinentes.
- Verificação de caminhos e circuitos de Euler.
- Funções auxiliares para calcular a rota ótima considerando itens obrigatórios e saída.

A validação da rota com coleta de itens não deve ser confundida com uma simples consulta de caminho mínimo entre dois vértices.

## 10.4. player.py

Responsável pelo estado do jogador:

- Andar atual.
- Andares visitados.
- Itens essenciais coletados.
- Itens bônus coletados.
- Quantidade de deslocamentos.
- Estado da fase.
- Histórico da rota percorrida.

## 10.5. game_controller.py

Responsável por processar as ações do jogador, controlar viagens por elevador, atualizar a exploração, verificar a coleta de itens e identificar quando a fase foi concluída.

## 10.6. level_manager.py

Responsável por carregar os arquivos das fases, configurar o estado inicial e validar os objetivos.

Cada fase deve ser definida por dados, evitando que seja necessário modificar a lógica geral do jogo para criar novos mapas.

## 10.7. score_manager.py

Responsável por calcular a pontuação, aplicar os bônus e registrar os resultados.

## 10.8. ui.py

Responsável por desenhar a interface em Pygame, incluindo o andar atual, destinos disponíveis, itens coletados, mapa parcial, mensagens e pontuação.

---

# 11. FORMATO DOS DADOS DAS FASES

Os arquivos de fase devem armazenar a configuração do prédio e seus objetivos.

Cada fase deverá definir:

- Identificador e nome da fase.
- Andar inicial.
- Andar de saída.
- Conjunto de andares.
- Conexões entre andares.
- Pesos das conexões, quando aplicável.
- Localização dos três itens essenciais.
- Localização dos três itens bônus.
- Restrições específicas da fase.
- Condições de conclusão.
- Configuração de pontuação.

Os dados devem ser validados durante o carregamento.

A validação deve verificar, no mínimo:

1. Todos os identificadores de andares são únicos.
2. Todas as conexões referenciam andares existentes.
3. Os três itens essenciais estão em andares distintos.
4. Os três itens bônus estão em andares distintos.
5. Nenhum item bônus compartilha andar com um item essencial.
6. Existem exatamente três itens essenciais e três itens bônus.
7. A saída é alcançável a partir do início.
8. Os três itens essenciais podem ser coletados em uma rota válida antes de alcançar a saída.
9. Nenhum item bônus é exigido para concluir a fase.
10. A fase respeita as condições matemáticas específicas de sua missão.

As fases devem ser criadas e testadas manualmente na primeira versão. Não é necessário implementar geração procedural de mapas.

---

# 12. TESTES E VALIDAÇÃO

Antes de considerar o projeto funcional, testar cada fase individualmente.

## 12.1. Testes de funcionamento

- O jogo inicia sem erros.
- Cada fase carrega os dados corretos.
- O jogador só pode utilizar conexões existentes.
- Os deslocamentos são contabilizados corretamente.
- Os itens são coletados uma única vez.
- Os itens coletados permanecem coletados após retornos.
- O mapa descoberto é atualizado corretamente.
- A fase não termina antes da coleta dos três itens essenciais.
- A fase termina quando todos os objetivos obrigatórios são cumpridos e o jogador alcança a saída.
- A ausência de itens bônus não bloqueia o progresso.

## 12.2. Testes matemáticos

- Dijkstra retorna um caminho mínimo válido para pesos não negativos.
- BFS calcula corretamente o número mínimo de arestas em grafos não ponderados.
- A validação de Euler distingue caminhos e circuitos.
- A validação de Hamilton verifica se todos os vértices exigidos são visitados exatamente uma vez.
- A rota ótima considera todos os itens essenciais e a saída.
- Quando a pontuação inclui bônus, a referência ótima considera os itens bônus coletados.
- As fases com restrições de Euler ou Hamilton possuem pelo menos uma solução válida.

## 12.3. Testes de impossibilidade

O jogo deve identificar configurações inválidas durante a preparação da fase, evitando apresentar ao jogador missões impossíveis por erro de projeto.

Não é necessário implementar um sistema sofisticado de geração automática de soluções para todas as fases, mas cada configuração deve ser verificada antes de ser considerada concluída.

---

# 13. REQUISITOS TÉCNICOS E LIMITES DO ESCOPO

A primeira versão deve priorizar a lógica do jogo e a aplicação da teoria dos grafos.

Requisitos obrigatórios:

- Python.
- Pygame.
- Execução local no computador.
- Cinco fases jogáveis.
- Interface gráfica funcional, mesmo que simples.
- Grafos definidos previamente.
- Exploração parcial do prédio.
- Três itens essenciais e três itens bônus por fase.
- Registro dos deslocamentos.
- Cálculo de pontuação.
- Verificação da conclusão das fases.
- Implementação própria dos algoritmos estudados.

Não implementar inicialmente:

- Multiplayer.
- Servidor ou conexão com a internet.
- Banco de dados.
- Geração procedural de fases.
- Combate.
- Física avançada.
- Sistema complexo de animação.
- Editor de mapas.
- Recursos gráficos elaborados.

O código deve ser modular, legível e comentado, especialmente nas partes matemáticas.

---

# 14. ORDEM DE IMPLEMENTAÇÃO

Desenvolva o projeto incrementalmente.

**Etapa 1 — Estrutura matemática**

Implementar a representação dos grafos, as listas de adjacência e os algoritmos básicos. Testar tudo sem interface gráfica.

**Etapa 2 — Protótipo jogável**

Criar a janela Pygame, a representação simples dos andares e a seleção dos elevadores.

**Etapa 3 — Exploração e itens**

Implementar a descoberta de conexões, o registro de andares visitados e a coleta dos itens essenciais e bônus.

**Etapa 4 — Conclusão e pontuação**

Implementar a saída, as condições de vitória, o cálculo dos deslocamentos e a pontuação.

**Etapa 5 — Criação das cinco fases**

Configurar os grafos e os itens de cada fase, verificando a existência de soluções válidas.

**Etapa 6 — Testes finais**

Testar o funcionamento, as regras matemáticas e os casos em que o jogador retorna a andares, ignora bônus ou tenta concluir uma fase sem os itens essenciais.

---

# 15. INSTRUÇÕES FINAIS PARA A IA DE PROGRAMAÇÃO

Com base nesta documentação, desenvolva o jogo Floor 13 em Python + Pygame.

Siga rigorosamente os requisitos definidos.

Priorize o funcionamento correto da lógica e das regras matemáticas antes de trabalhar na aparência visual.

Não implemente todas as funcionalidades de uma vez. Comece pela representação do grafo e pelos testes dos algoritmos; em seguida, desenvolva uma primeira fase completamente funcional. Só depois de validar essa fase, implemente as demais.

Não invente regras que alterem os objetivos estabelecidos.

Em particular:

- Os itens bônus devem estar em andares exclusivos, diferentes dos andares dos itens essenciais.
- Os itens bônus são opcionais e nunca podem bloquear a saída ou impedir a conclusão.
- O jogador deve poder terminar uma fase coletando somente os três itens essenciais.
- A rota ótima deve considerar os itens obrigatórios e a saída, e não apenas a distância entre dois andares.
- O jogo não deve obrigar a visitar todos os andares em fases nas quais a exploração de andares opcionais seja permitida.
- Caminhos de Euler e Hamilton devem ser tratados como problemas distintos.
- As fases devem ser matematicamente verificadas antes de serem consideradas prontas.
- A interface pode ser simples, com texto, botões e formas geométricas.
- Não utilize imagens ou recursos externos como dependência obrigatória para que o jogo funcione.

Ao concluir cada etapa, informe quais arquivos foram criados, quais funcionalidades estão operacionais e quais testes foram realizados.

O resultado esperado é um protótipo jogável de cinco fases que demonstre, de forma prática, como a teoria dos grafos pode ser aplicada à exploração, ao planejamento de rotas e à otimização de deslocamentos.

---

# 16. IMPLEMENTAÇÃO ATUAL — PRIMEIRA FASE

Além da estrutura matemática e da interface inicial, a fase **Primeiro
contato** já tem seis andares, exploração, itens obrigatórios e bônus, coleta e
condição de vitória. Os dados e a validação da fase ficam fora da apresentação
gráfica, e as regras de progresso são reutilizáveis por futuras fases.

Para instalar a biblioteca gráfica e executar o protótipo no Windows:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Na janela:

- Selecione um destino conectado clicando nele ou usando as teclas `1` a `6`.
- Viaje com **VIAJAR** ou `Enter`.
- Colete itens disponíveis no andar com **COLETAR** ou `E`. Os bônus são
  opcionais.
- `Esc` fecha o jogo.

Para executar os testes matemáticos e de progressão:

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem a estrutura do grafo, BFS e Dijkstra, conectividade,
movimentação, exploração, coleta, saída bloqueada, conclusão da fase e a
possibilidade de vencer sem bônus. Os desafios de Euler/Hamilton, pontuação,
salvamento e as outras fases ainda não foram implementados.
