# Changelog

Todas as mudanças notáveis neste projeto são documentadas neste arquivo.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [2026.08.26] — 2026-08-26

Revisão geral trazendo a versão NVDA para o mesmo nível de recursos e
correções já presentes na versão Windows.

### Corrigido

- **Leitor de tela anunciava o botão errado ao entrar na área de leitura:** sem um rótulo próprio, o NVDA usava o nome do último botão criado antes dela como referência. Adicionado o rótulo "Leitura:".
- **Setas esquerda/direita sem bloqueio fora da lista de versículos:** em outras listas (livros, capítulos, busca...), essas setas aplicavam o comportamento padrão de navegação de coluna única do Windows, dando a impressão de estar "folheando" algo sem função real ali. Bloqueadas fora do contexto certo.
- **Botão "Marcar capítulo como lido" ficava habilitado nas telas de Busca e Favoritos:** sem sentido nesses contextos, já que não há um "capítulo atual" claro pra marcar. Corrigido.
- **Tema escuro/claro nunca era salvo:** o addon sempre reabria no tema escuro, ignorando a última escolha do usuário — bug presente em três pontos (inicialização, alternância pelo menu, e reaplicação após restaurar um backup). Corrigido com persistência de verdade no arquivo de configuração.
- **Diálogo "Continuar leitura" sem centralização:** faltava `CenterOnParent()`, o mesmo problema já identificado e corrigido antes na versão Windows.
- **Links desatualizados para o Google Drive:** trocados pela página oficial de Bíblias (openbible.com.br/windows/biblias).

### Adicionado

- **Bip discreto ao navegar por um capítulo já lido:** sinalização sutil (880 Hz, 15 ms) na lista de capítulos.
- **Backup e restauração agora incluem as Bíblias instaladas**, com opção de substituir a coleção inteira ao restaurar em vez de só somar arquivos por cima dos já existentes.
- **Duas opções novas no menu Exibição:** "Perguntar se deseja continuar a leitura ao abrir" e "Perguntar antes de fechar o Open Bible" — a lógica já existia internamente, mas não havia como o usuário alterar essas preferências.
- **Barra de status**, mostrando versão da Bíblia, livro/capítulo e versículo atual.
- **Formatação visual na área de leitura:** título do capítulo em destaque e números de versículo em negrito.
- **Pasta de Bíblias agora fica oculta no Explorer**, mesmo tratamento já aplicado na versão Windows.

### Alterado

- **Botões reorganizados em grupos visuais** (Navegação, Ações, Busca, Favoritos), com molduras que aparecem e somem conforme o contexto — mesma organização já usada na versão Windows.
- **Texto do "Sobre" reescrito**, com mais contexto sobre o propósito do programa.

---

## [2026.06.15] — 2026-06-15

### Corrigido

- **NVDA anunciava "Open" ao iniciar:** o campo de texto recebia `"Open Bible\n\nSelecione um livro."` e o NVDA lia o conteúdo ao focar. Texto removido.
- **`Ctrl+R` (Ir para referência) não funcionava:** erro de regex (`\\\\d+` em vez de `\\d+`) impedia qualquer referência de ser encontrada. Corrigido.
- **Janela "sem Bíblia" não era rastreada:** o frame era criado em variável local em vez de `self._frame`, impedindo reabertura e destruição corretas. Corrigido.
- **`_speakRandomFavorite` travava na inicialização:** chamada a `speech.speakMessage` sem proteção falhava se o NVDA ainda não estivesse pronto. Adicionado `try/except`.
- **Dispatch de timers impreciso:** comparação por identidade de objeto (`is`) substituída por comparação de ID, mais confiável no wxPython.
- **Frame destruído não era detectado:** `_iniciar_interface` só verificava `IsShown()`; se o frame tivesse sido destruído internamente, lançava exceção. Adicionado tratamento adequado com descarte e recriação.

### Alterado

- **Eliminado anúncio duplo de "painel":** o mecanismo de troca entre `ListCtrl` e `ListBox` (via `.Hide()/.Show()`) reorganizava o layout e fazia o NVDA perder o foco. Substituído por um único `ListBox` fixo.
- **"Selecione um livro" removido:** frase redundante eliminada da abertura e da navegação de volta para o índice. O NVDA já anuncia o título da janela e o foco na lista automaticamente. Mantida apenas na mensagem de troca de versão.
- **Delay de inicialização dinâmico:** o tempo de espera antes de anunciar "Selecione um livro" era fixo (800 ms). Agora é calculado pelo tamanho do nome da versão (`1200 ms + 60 ms/caractere`), evitando que o título da janela seja cortado.
- **Leitura contínua — início:** "Leitura contínua iniciada" e o primeiro versículo eram falados simultaneamente. Adicionado atraso de 700 ms antes do primeiro versículo.
- **Leitura contínua — pausa:** ao pausar, o verso em andamento continuava sendo falado. Adicionado `speech.cancelSpeech()` imediato, com "Leitura interrompida" após 150 ms.
- **Leitura contínua — retomada:** `CallLater` residual de sessões anteriores causava pulo de 1 ou 2 versículos ao retomar. Resolvido com sistema de token de sessão que invalida chamadas de sessões anteriores.
- **Leitura contínua — timing:** intervalo entre versículos ajustado para `400 ms base + 13 ms/caractere` (mínimo 800 ms, máximo 8 s), cobrindo melhor a velocidade real do NVDA.

### Adicionado

- **Bip ao retornar ao índice de livros:** ao pressionar Escape em capítulos, busca, favoritos ou lidos, um bip curto (440 Hz, 40 ms) avisa que o próximo Escape fechará o programa.

---

## [2026.05.01] — 2026-05-01

### Adicionado

- Compatibilidade com NVDA 2026.1.

---

## [2025.1.0] — 2025-01-01

- Versão inicial pública.
