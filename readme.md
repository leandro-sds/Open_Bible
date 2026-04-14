# Open Bible (NVDA Add-on)

Add-on do **NVDA** para leitura da Bíblia Sagrada totalmente acessível, com suporte a múltiplas versões (arquivos `.json`), navegação por livro, capítulo e versículo, pesquisa, favoritos, anotações e muito mais.

**Atalho para abrir:** `Ctrl+Alt+B`

## Instalação

1. Baixe o arquivo `.nvda-addon` na página de [releases do GitHub](https://github.com/leandro-sds/Open_Bible/releases).
2. Abra o arquivo e confirme a instalação no NVDA.
3. Reinicie o NVDA se solicitado.
4. Pressione `Ctrl+Alt+B` para abrir o Open Bible.
5. Na primeira abertura sem Bíblia instalada, o addon perguntará se deseja abrir o Google Drive para baixar os arquivos. Após baixar, use `Ctrl+G` para importar o arquivo `.json`.

## Adicionar versões da Bíblia

O Open Bible usa arquivos `.json` como fonte de dados. Para adicionar uma versão:

1. Abra o Open Bible (`Ctrl+Alt+B`).
2. Pressione `Ctrl+G` para abrir o Gerenciador de Bíblias.
3. Clique em **Importar JSON** e selecione o arquivo baixado.
4. A versão será carregada automaticamente.

Arquivos disponíveis para download: [Google Drive – Bíblias Open Bible](https://drive.google.com/drive/folders/1THS2L9GiCx_rWWCJ23JGh3Ws7qVup0uE?usp=sharing)

Exemplos de nomes de arquivo: `01_ACF.json`, `02_NVI.json`.

## Navegação

A navegação segue a hierarquia: **Livros → Capítulos → Versículos**.

- Use as **setas** para mover entre itens da lista.
- Pressione **Enter** ou **duplo clique** para abrir o item selecionado.
- Pressione **Esc** para voltar ao nível anterior.
- Use **Esquerda** e **Direita** para navegar entre capítulos (e entre livros ao chegar no primeiro ou último capítulo).

## Recursos

- **Múltiplas versões:** carregue e alterne entre versões da Bíblia.
- **Pesquisa:** busca por palavra ou frase em toda a Bíblia ou em um livro específico, com opção de palavra inteira e ignorar acentos.
- **Ir para referência:** navegue diretamente para qualquer referência bíblica (ex.: Jo 3:16).
- **Ir para número (F5):** vá diretamente a um capítulo ou versículo pelo número, com mensagem de erro se o número não existir.
- **Favoritos:** adicione, liste e remova versículos favoritos, com paginação.
- **Anotações:** adicione notas a capítulos ou versículos específicos.
- **Copiar versículos:** copie o versículo atual, uma seleção múltipla ou resultados de busca para a área de transferência.
- **Seleção múltipla:** marque vários versículos com Espaço e copie todos de uma vez.
- **Leitura contínua:** leitura automática sequencial do capítulo (`Ctrl+L`).
- **Comparar versões:** compare um versículo entre diferentes versões da Bíblia lado a lado (`Ctrl+Shift+C`).
- **Histórico de leitura:** marque capítulos como lidos e consulte o histórico (`Ctrl+M` / `Ctrl+Shift+M`).
- **Versículo ao iniciar:** leitura automática de um favorito aleatório ao iniciar o NVDA (configurável em Exibição).
- **Tema escuro/claro:** alternância visual pelo menu Exibição.
- **Ajuste de fonte:** `Ctrl++` e `Ctrl+-`.
- **Backup e restauração:** salve e restaure configurações, favoritos, notas e histórico em ZIP (`Ctrl+B`).
- **Gerenciador de Bíblias:** importe, remova e defina a versão padrão (`Ctrl+G`).

## Atalhos

| Atalho | Função |
|---|---|
| Ctrl+Alt+B | Abrir o Open Bible |
| Esc | Voltar ao nível anterior |
| Enter | Abrir item / ouvir versículo |
| Espaço | Marcar/desmarcar versículo |
| Ctrl+A | Marcar todos os versículos |
| Ctrl+Z | Limpar seleção |
| Ctrl+C | Copiar versículo(s) |
| Ctrl+E | Editor de versículo (somente leitura) |
| Ctrl+I | Índice de livros |
| Ctrl+L | Iniciar/Parar leitura contínua |
| Esquerda / Direita | Capítulo anterior / próximo (e livro anterior/próximo nos extremos) |
| Ctrl+Shift+C | Comparar versículo entre versões |
| PageUp / PageDown | Página anterior / próxima (busca, favoritos e lidos) |
| F5 | Ir para capítulo ou versículo por número |
| F1 | Ajuda rápida com todos os atalhos |
| Ctrl+P | Pesquisar na Bíblia |
| Ctrl+R | Ir para referência (ex.: Jo 3:16) |
| Ctrl+N | Adicionar nota |
| Ctrl+Del | Remover nota selecionada |
| Ctrl+F | Adicionar favorito |
| Ctrl+Shift+F | Abrir lista de favoritos |
| Ctrl+M | Marcar/desmarcar capítulo como lido |
| Ctrl+Shift+M | Listar capítulos lidos |
| Ctrl+T | Alternar para a próxima versão (cíclico) |
| Ctrl+G | Gerenciar Bíblias |
| Ctrl+B | Backup e restauração |
| Ctrl++ / Ctrl+- | Aumentar / diminuir fonte da área de leitura |
| Alt+F4 | Fechar o Open Bible |

## Licença

Distribuído sob a **GPL v2** (veja `COPYING.txt`).

## Créditos

Desenvolvido por **Leandro Souza**.  
GitHub: [github.com/leandro-sds/Open_Bible](https://github.com/leandro-sds/Open_Bible/)
