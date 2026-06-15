# Open Bible

Add-on do **NVDA** para leitura da Bíblia Sagrada totalmente acessível.
Suporte a múltiplas versões em formato `.json`, com navegação por livro, capítulo e versículo, pesquisa, favoritos, anotações e muito mais.

[![Licença: GPL v2](https://img.shields.io/badge/Licença-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

---

## Requisitos

- NVDA 2024.1 ou superior
- Windows 10 ou superior

---

## Instalação

1. Baixe o arquivo `.nvda-addon` na página de [releases](https://github.com/leandro-sds/Open_Bible/releases).
2. Abra o arquivo baixado; o NVDA solicitará confirmação de instalação.
3. Reinicie o NVDA se solicitado.
4. Pressione `Ctrl+Alt+B` para abrir o Open Bible.

Na primeira abertura sem nenhuma Bíblia instalada, o add-on perguntará se deseja abrir o Google Drive para baixar os arquivos de versões.

---

## Adicionar versões da Bíblia

O Open Bible usa arquivos `.json` como fonte de dados. Para adicionar uma versão:

1. Abra o Open Bible (`Ctrl+Alt+B`).
2. Pressione `Ctrl+G` para abrir o Gerenciador de Bíblias.
3. Clique em **Importar JSON** e selecione o arquivo baixado.
4. A versão será carregada automaticamente.

**Arquivos disponíveis:** [Google Drive – Bíblias Open Bible](https://drive.google.com/drive/folders/1THS2L9GiCx_rWWCJ23JGh3Ws7qVup0uE?usp=sharing)

Exemplos de nomes de arquivo: `01_ACF.json`, `02_NVI.json`.

---

## Navegação

A navegação segue a hierarquia: **Livros → Capítulos → Versículos**.

| Ação | Resultado |
|---|---|
| Setas | Mover entre itens da lista |
| Enter ou duplo clique | Abrir o item selecionado |
| Escape | Voltar ao nível anterior |
| Seta esquerda / direita | Capítulo anterior / próximo (e livro anterior/próximo nos extremos) |

Ao retornar ao índice de livros, um bip curto avisa que o próximo Escape fechará o programa.

---

## Recursos

- **Múltiplas versões:** carregue e alterne entre versões da Bíblia (`Ctrl+T`).
- **Pesquisa:** busca por palavra ou frase em toda a Bíblia ou em um livro específico, com opção de palavra inteira e ignorar acentos (`Ctrl+P`).
- **Ir para referência:** navegue diretamente para qualquer referência bíblica, ex.: `Jo 3:16` (`Ctrl+R`).
- **Ir para número:** vá diretamente a um capítulo ou versículo pelo número (`F5`).
- **Favoritos:** adicione, liste e remova versículos favoritos, com paginação (`Ctrl+F` / `Ctrl+Shift+F`).
- **Anotações:** adicione notas a capítulos ou versículos específicos (`Ctrl+N`).
- **Copiar versículos:** copie o versículo atual, uma seleção múltipla ou resultados de busca (`Ctrl+C`).
- **Seleção múltipla:** marque vários versículos com Espaço e copie todos de uma vez.
- **Leitura contínua:** leitura automática sequencial do capítulo (`Ctrl+L`). Pausa e retoma a partir do versículo seguinte.
- **Comparar versões:** compare um versículo entre diferentes versões lado a lado (`Ctrl+Shift+C`).
- **Histórico de leitura:** marque capítulos como lidos e consulte o histórico (`Ctrl+M` / `Ctrl+Shift+M`).
- **Versículo ao iniciar:** leitura automática de um favorito aleatório ao iniciar o NVDA (configurável em Exibição).
- **Tema escuro/claro:** alternância visual pelo menu Exibição.
- **Ajuste de fonte:** `Ctrl++` e `Ctrl+-`.
- **Backup e restauração:** salve e restaure configurações, favoritos, notas e histórico em ZIP (`Ctrl+B`).
- **Gerenciador de Bíblias:** importe, remova e defina a versão padrão (`Ctrl+G`).

---

## Atalhos

| Atalho | Função |
|---|---|
| `Ctrl+Alt+B` | Abrir o Open Bible |
| `Esc` | Voltar ao nível anterior / fechar |
| `Enter` | Abrir item / ouvir versículo |
| `Espaço` | Marcar/desmarcar versículo |
| `Ctrl+A` | Marcar todos os versículos |
| `Ctrl+Z` | Limpar seleção |
| `Ctrl+C` | Copiar versículo(s) |
| `Ctrl+E` | Editor de versículo (somente leitura) |
| `Ctrl+I` | Índice de livros |
| `Ctrl+L` | Iniciar/Parar leitura contínua |
| `Seta esquerda / direita` | Capítulo anterior / próximo |
| `Ctrl+Shift+C` | Comparar versículo entre versões |
| `PageUp / PageDown` | Página anterior / próxima (busca, favoritos, lidos) |
| `F5` | Ir para capítulo ou versículo por número |
| `F1` | Ajuda rápida com todos os atalhos |
| `Ctrl+P` | Pesquisar na Bíblia |
| `Ctrl+R` | Ir para referência (ex.: Jo 3:16) |
| `Ctrl+N` | Adicionar nota |
| `Ctrl+Del` | Remover nota selecionada |
| `Ctrl+F` | Adicionar favorito |
| `Ctrl+Shift+F` | Abrir lista de favoritos |
| `Ctrl+M` | Marcar/desmarcar capítulo como lido |
| `Ctrl+Shift+M` | Listar capítulos lidos |
| `Ctrl+T` | Alternar para a próxima versão (cíclico) |
| `Ctrl+G` | Gerenciar Bíblias |
| `Ctrl+B` | Backup e restauração |
| `Ctrl++` / `Ctrl+-` | Aumentar / diminuir fonte da área de leitura |
| `Alt+F4` | Fechar o Open Bible |

---

## Changelog

Veja o arquivo [changelog.md](changelog.md) para o histórico completo de alterações.

---

## Licença

Distribuído sob a [GNU General Public License v2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).

---

## Créditos

Desenvolvido por **Leandro Souza**.
GitHub: [github.com/leandro-sds/Open_Bible](https://github.com/leandro-sds/Open_Bible)
