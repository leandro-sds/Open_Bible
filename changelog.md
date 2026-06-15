# Changelog

Todas as mudanças notáveis neste projeto são documentadas neste arquivo.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

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
