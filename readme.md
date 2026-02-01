# Open Bible (NVDA Add-on)

Add-on do **NVDA** para leitura da Bíblia Sagrada em várias versões (arquivos JSON), com navegação por **livro → capítulo → versículo**, pesquisa e recursos de produtividade.

- **Atalho principal:** `Ctrl+Alt+B` (abre a janela do Open Bible)

## Recursos

- Seleção de **versões** (arquivos `.json`) e gerenciamento das versões instaladas
- Navegação rápida por livro, capítulo e versículo
- **Pesquisa** de texto
- **Favoritos** e **anotações**
- **Copiar/compartilhar** versículos (área de transferência do Windows)

## Pasta `biblias/` (não incluída neste ZIP)

Por padrão, o add-on procura as versões em `addon/biblias/` (sem acento).  

Exemplos de nomes de arquivo:
- `01_ACF.json`
- `02_NVI.json`

## Instalação (usuário final)

1. Baixe o arquivo `*.nvda-addon` na página de releases do GitHub.
2. Abra o arquivo e confirme a instalação no NVDA.
3. Reinicie o NVDA se solicitado.
4. Use `Ctrl+Alt+B` para abrir o Open Bible.

## Desenvolvimento / Compilação do add-on

Este repositório usa o template oficial com **SCons**.

Requisitos (Linux / GitHub Actions):
- Python 3.11+
- `gettext`
- `scons`, `pre-commit`, `markdown`

Comandos:
```bash
python -m pip install -U pip wheel
pip install scons pre-commit markdown
scons
```

Para gerar o arquivo POT (traduções):
```bash
scons pot
```

## Licença

Este projeto é distribuído sob a **GPL v2** (veja `COPYING.txt`).

## Créditos

Desenvolvido por **Leandro Souza**.
