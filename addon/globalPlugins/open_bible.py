import wx
import globalPluginHandler
import addonHandler
import json
import os
import re
import shutil
import unicodedata
import webbrowser
import random
import speech
import zipfile
import datetime
from collections import defaultdict
from scriptHandler import script

try:
	import ui
except Exception:
	ui = None

try:
	import gui
except Exception:
	gui = None

try:
	import config as nvdaConfig
except Exception:
	nvdaConfig = None

try:
	import win32clipboard
	import win32con
except Exception:
	win32clipboard = None
	win32con = None

addonHandler.initTranslation()
_ = addonHandler.gettext

def get_nvda_user_config_dir():
	if nvdaConfig and hasattr(nvdaConfig, "getUserDefaultConfigPath"):
		try:
			return nvdaConfig.getUserDefaultConfigPath()
		except Exception:
			pass

	try:
		import globalVars
		if hasattr(globalVars, "appArgs") and hasattr(globalVars.appArgs, "configPath"):
			return globalVars.appArgs.configPath
	except Exception:
		pass

	appdata = os.environ.get("APPDATA")
	if appdata:
		return os.path.join(appdata, "nvda")
	return os.path.expanduser("~")

PLUGIN_BASE_DIR = os.path.dirname(__file__)
NVDA_CONFIG_BASE = os.path.join(get_nvda_user_config_dir(), "openBible")

def _ensure_dir(path):
	try:
		absPath = os.path.abspath(path)
		parent = os.path.dirname(absPath)
		if not os.path.isdir(parent):
			return False
		os.makedirs(absPath, exist_ok=True)
		return True
	except Exception:
		return False

def _ensure_addon_config_dir():
	return _ensure_dir(NVDA_CONFIG_BASE)

class ConfigManager:
	def __init__(self):
		_ensure_addon_config_dir()
		self.configPath = os.path.join(NVDA_CONFIG_BASE, "config.json")
		self.data = self._load()

	def _load(self):
		try:
			if os.path.exists(self.configPath):
				with open(self.configPath, "r", encoding="utf-8") as f:
					return json.load(f)
			data = {}
			self._save_direct(data)
			return data
		except Exception:
			return {}

	def _save(self):
		self._save_direct(self.data)

	def _save_direct(self, data):
		try:
			with open(self.configPath, "w", encoding="utf-8") as f:
				json.dump(data, f, ensure_ascii=False, indent=2)
		except Exception:
			if ui:
				ui.message("Open Bible: Não foi possível salvar a configuração.")

	def get_version(self):
		return self.data.get("versao")

	def set_version(self, versao):
		self.data["versao"] = versao
		self._save()

	def get_last_position(self, versao):
		posicoes = self.data.get("ultimaPosicao", {})
		pos = posicoes.get(versao)
		if isinstance(pos, dict) and {"livro", "capitulo"} <= set(pos.keys()):
			return pos["livro"], pos["capitulo"]
		return None, None

	def set_last_position(self, versao, livro, capitulo):
		if "ultimaPosicao" not in self.data or not isinstance(self.data.get("ultimaPosicao"), dict):
			self.data["ultimaPosicao"] = {}
		self.data["ultimaPosicao"][versao] = {"livro": livro, "capitulo": capitulo}
		self._save()

	def get_skip_continue_prompt(self):
		return bool(self.data.get("naoMostrarContinuar"))

	def set_skip_continue_prompt(self, flag: bool):
		self.data["naoMostrarContinuar"] = bool(flag)
		self._save()

	def get_skip_exit_prompt(self):
		return bool(self.data.get("naoPerguntarFechar"))

	def set_skip_exit_prompt(self, flag: bool):
		self.data["naoPerguntarFechar"] = bool(flag)
		self._save()

	def get_speak_on_startup(self):
		return bool(self.data.get("falarFavoritoAoIniciar", False))

	def set_speak_on_startup(self, flag: bool):
		self.data["falarFavoritoAoIniciar"] = bool(flag)
		self._save()

class FavoritesManager:
	def __init__(self):
		_ensure_addon_config_dir()
		self.path = os.path.join(NVDA_CONFIG_BASE, "favoritos.json")
		self.favoritos = self._load()

	def _load(self):
		try:
			if os.path.exists(self.path):
				with open(self.path, "r", encoding="utf-8") as f:
					data = json.load(f)
				data = [
					f for f in data
					if isinstance(f, dict)
					and {"livro", "capitulo", "versiculo", "texto"} <= set(f.keys())
				]
				return data
			with open(self.path, "w", encoding="utf-8") as f:
				json.dump([], f, ensure_ascii=False, indent=2)
			return []
		except Exception:
			return []

	def all(self):
		return list(self.favoritos)

	def add_many(self, items):
		existing = {(f["livro"], f["capitulo"], f["versiculo"], f["texto"]) for f in self.favoritos}
		new_unique = []
		for it in items:
			key = (it["livro"], it["capitulo"], it["versiculo"], it["texto"])
			if key not in existing:
				new_unique.append(it)
		if new_unique:
			self.favoritos = new_unique + self.favoritos
			self._save()

	def remove_at_index(self, idx):
		if 0 <= idx < len(self.favoritos):
			del self.favoritos[idx]
			self._save()

	def _save(self):
		try:
			with open(self.path, "w", encoding="utf-8") as f:
				json.dump(self.favoritos, f, ensure_ascii=False, indent=2)
		except Exception as e:
			if ui:
				ui.message(f"Erro ao salvar favoritos: {e}")

class ReadChaptersManager:
	def __init__(self):
		_ensure_addon_config_dir()
		self.path = os.path.join(NVDA_CONFIG_BASE, "capitulos_lidos.json")
		self.lidos = self._load()
		self._lidos_set = self._build_set()

	def _build_set(self):
		return {(item["livro"], item["capitulo"]) for item in self.lidos}

	def _load(self):
		try:
			if os.path.exists(self.path):
				with open(self.path, "r", encoding="utf-8") as f:
					data = json.load(f)
				data = [
					item for item in data
					if isinstance(item, dict) and {"livro", "capitulo"} <= set(item.keys())
				]
				return data
			with open(self.path, "w", encoding="utf-8") as f:
				json.dump([], f, ensure_ascii=False, indent=2)
			return []
		except Exception:
			return []

	def is_read(self, livro, capitulo):
		return (livro, capitulo) in self._lidos_set

	def mark_read(self, livro, capitulo):
		self.remove(livro, capitulo)
		self.lidos.insert(0, {"livro": livro, "capitulo": capitulo})
		self._lidos_set.add((livro, capitulo))
		self._save()

	def remove(self, livro, capitulo):
		self.lidos = [
			item for item in self.lidos
			if not (item["livro"] == livro and item["capitulo"] == capitulo)
		]
		self._lidos_set.discard((livro, capitulo))
		self._save()

	def all(self):
		return list(self.lidos)

	def _save(self):
		try:
			with open(self.path, "w", encoding="utf-8") as f:
				json.dump(self.lidos, f, ensure_ascii=False, indent=2)
		except Exception:
			pass

class BibleManager:
	def __init__(self, pluginBaseDir):
		self.baseDir = pluginBaseDir
		self.bibliasDir = os.path.join(self.baseDir, "biblias")
		self.versoes = self._detectarVersoes()
		self.versaoAtual = None
		self.bible_tree = {}
		self.indexPorLivro = defaultdict(list)
		self.indexCapPorLivro = defaultdict(set)

	def _detectarVersoes(self):
		versoes = {}
		try:
			if not os.path.isdir(self.bibliasDir):
				os.makedirs(self.bibliasDir, exist_ok=True)
			for f in sorted(os.listdir(self.bibliasDir)):
				if f.lower().endswith(".json"):
					base = f[:-5]
					nome = base.split("_", 1)[-1] if "_" in base else base
					versoes[nome] = os.path.join(self.bibliasDir, f)
		except Exception:
			pass
		return versoes

	def listar_nomes(self):
		return list(self.versoes.keys())

	def has_versions(self):
		return bool(self.versoes)

	def carregar(self, versao):
		caminho = self.versoes.get(versao)
		if not caminho:
			raise FileNotFoundError(f"Versão '{versao}' não encontrada.")
		with open(caminho, "r", encoding="utf-8") as f:
			biblia = json.load(f)

		self.bible_tree = defaultdict(lambda: defaultdict(list))
		self.indexPorLivro.clear()
		self.indexCapPorLivro.clear()

		bt = self.bible_tree
		ipl = self.indexPorLivro
		icpl = self.indexCapPorLivro

		for v in biblia:
			livro = v["livro"]
			cap = v["capitulo"]
			bt[livro][cap].append(v)
			ipl[livro].append(v)
			icpl[livro].add(cap)

		self.versaoAtual = versao
		return biblia

	def carregar_para_leitura(self, versao):
		caminho = self.versoes.get(versao)
		if not caminho:
			raise FileNotFoundError(f"Versão '{versao}' não encontrada.")
		with open(caminho, "r", encoding="utf-8") as f:
			biblia = json.load(f)
		return biblia

	def adicionar_arquivo_json(self, origem):
		if not os.path.isfile(origem) or not origem.lower().endswith(".json"):
			raise ValueError("Arquivo inválido. Selecione um .json.")
		os.makedirs(self.bibliasDir, exist_ok=True)
		nomeArquivo = os.path.basename(origem)
		destino = os.path.join(self.bibliasDir, nomeArquivo)
		shutil.copy2(origem, destino)
		base = nomeArquivo[:-5]
		nome = base.split("_", 1)[-1] if "_" in base else base
		self.versoes[nome] = destino

	def remover_versao(self, versao):
		caminho = self.versoes.get(versao)
		if not caminho:
			raise FileNotFoundError("Versão não encontrada.")
		try:
			os.remove(caminho)
		except Exception as e:
			raise RuntimeError(f"Falha ao remover arquivo: {e}")
		self.versoes.pop(versao, None)

class NotesManager:
	def __init__(self, versao):
		_ensure_addon_config_dir()
		self.versao = versao
		self.path = os.path.join(NVDA_CONFIG_BASE, f"notas_{versao}.json")
		self.notas = self._load()

	def _load(self):
		try:
			if os.path.exists(self.path):
				with open(self.path, "r", encoding="utf-8") as f:
					data = json.load(f)
				data = [
					n for n in data
					if isinstance(n, dict) and {"livro", "capitulo", "nota"} <= set(n.keys())
				]
				return data
			with open(self.path, "w", encoding="utf-8") as f:
				json.dump([], f, ensure_ascii=False, indent=2)
			return []
		except Exception:
			return []

	def all(self):
		return self.notas

	def add(self, nota):
		self.notas.append(nota)
		self._save()

	def remove(self, nota):
		try:
			self.notas.remove(nota)
			self._save()
		except ValueError:
			pass

	def _save(self):
		try:
			with open(self.path, "w", encoding="utf-8") as f:
				json.dump(self.notas, f, ensure_ascii=False, indent=2)
		except Exception as e:
			if ui:
				ui.message(f"Erro ao salvar notas da versão {self.versao}: {e}")

NOMES_LIVROS = {
	"Gn": "Gênesis", "Ex": "Êxodo", "Lv": "Levítico", "Nm": "Números", "Dt": "Deuteronômio",
	"Js": "Josué", "Jz": "Juízes", "Rt": "Rute", "1Sm": "1º Samuel", "2Sm": "2º Samuel",
	"1Rs": "1º Reis", "2Rs": "2º Reis", "1Cr": "1º Crônicas", "2Cr": "2º Crônicas",
	"Ed": "Esdras", "Ne": "Neemias", "Tb": "Tobias", "Jt": "Judite", "Et": "Ester",
	"1Mc": "1º Macabeus", "2Mc": "2º Macabeus",
	"Jó": "Jó", "Sl": "Salmos", "Pv": "Provérbios", "Ec": "Eclesiastes", "Ct": "Cânticos",
	"Sb": "Sabedoria", "Eclo": "Eclesiástico",
	"Is": "Isaías", "Jr": "Jeremias", "Lm": "Lamentações", "Br": "Baruc", "Ez": "Ezequiel", "Dn": "Daniel",
	"Os": "Oseias", "Jl": "Joel", "Am": "Amós", "Ob": "Obadias", "Jn": "Jonas",
	"Mq": "Miquéias", "Na": "Naum", "Hc": "Habacuque", "Sf": "Sofonias", "Ag": "Ageu",
	"Zc": "Zacarias", "Ml": "Malaquias",
	"Mt": "Mateus", "Mc": "Marcos", "Lc": "Lucas", "Jo": "João", "At": "Atos",
	"Rm": "Romanos", "1Co": "1ª Coríntios", "2Co": "2ª Coríntios", "Gl": "Gálatas", "Ef": "Efésios",
	"Fp": "Filipenses", "Cl": "Colossenses", "1Ts": "1ª Tessalonicenses", "2Ts": "2ª Tessalonicenses",
	"1Tm": "1ª Timóteo", "2Tm": "2ª Timóteo", "Tt": "Tito", "Fm": "Filemom", "Hb": "Hebreus",
	"Tg": "Tiago", "1Pe": "1ª Pedro", "2Pe": "2ª Pedro", "1Jo": "1ª João", "2Jo": "2ª João", "3Jo": "3ª João",
	"Jd": "Judas", "Ap": "Apocalipse"
}

def normalizar(txt):
	return ''.join(
		c for c in unicodedata.normalize('NFD', txt)
		if unicodedata.category(c) != 'Mn'
	).lower()

class ListaWrapper(wx.ListCtrl):
	def __init__(self, parent, name="Lista de seleção"):
		super().__init__(
			parent,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER,
			name=name
		)
		self._itens = []
		col = wx.ListItem()
		col.SetText("")
		col.SetWidth(-2)
		self.InsertColumn(0, col)
		self.Bind(wx.EVT_SIZE, self._onResize)

	def _onResize(self, event):
		try:
			w = self.GetClientSize().width
			if w > 0:
				self.SetColumnWidth(0, w)
		except Exception:
			pass
		event.Skip()

	def _syncColWidth(self):
		try:
			w = self.GetClientSize().width
			if w > 0:
				self.SetColumnWidth(0, w)
		except Exception:
			pass

	def Clear(self):
		self.DeleteAllItems()
		self._itens = []

	def GetCount(self):
		return self.GetItemCount()

	def GetString(self, idx):
		if 0 <= idx < len(self._itens):
			return self._itens[idx]
		return ""

	def SetString(self, idx, s):
		if 0 <= idx < len(self._itens):
			self._itens[idx] = s
			self.SetItemText(idx, s)

	def Append(self, s):
		idx = self.InsertItem(self.GetItemCount(), s)
		self._itens.append(s)
		return idx

	def AppendItems(self, strings):
		self.Freeze()
		try:
			for s in strings:
				self.InsertItem(self.GetItemCount(), s)
				self._itens.append(s)
			self._syncColWidth()
		finally:
			self.Thaw()

	def Delete(self, idx):
		if 0 <= idx < self.GetItemCount():
			self.DeleteItem(idx)
			if 0 <= idx < len(self._itens):
				del self._itens[idx]

	def GetSelection(self):
		idx = self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
		return idx if idx != -1 else wx.NOT_FOUND

	def SetSelection(self, idx):
		current = self.GetSelection()
		if current != wx.NOT_FOUND and current != idx:
			self.SetItemState(current, 0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
		if idx == wx.NOT_FOUND:
			return
		count = self.GetItemCount()
		if 0 <= idx < count:
			self.SetItemState(idx, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)

	def EnsureVisible(self, idx):
		count = self.GetItemCount()
		if 0 <= idx < count:
			super().EnsureVisible(idx)

	def SetBackgroundColour(self, colour):
		super().SetBackgroundColour(colour)

	def SetForegroundColour(self, colour):
		super().SetForegroundColour(colour)

class BibliaFrame(wx.Frame):
	def __init__(self, biblia, notas, bibleManager, notesManager, versaoAtual, configManager, favoritesManager):
		super().__init__(None, title="Open Bible", size=(1100, 750))
		self.biblia = biblia or []
		self.notas = notas or []
		self.bibleManager = bibleManager
		self.notesManager = notesManager
		self.configManager = configManager
		self.favoritesManager = favoritesManager
		self.readManager = ReadChaptersManager()
		self.versaoAtual = versaoAtual

		self.nivel = "livros"
		self.livroAtual = None
		self.capituloAtual = None
		self.capitulos = []
		self.resultadosBusca = []
		self.paginaAtual = 0
		self.itensPorPagina = 18

		self.leituraAtiva = False
		self.leituraTimer = wx.Timer(self)
		self.leituraIndice = 0
		self._leituraTotalVersos = 0
		self.Bind(wx.EVT_TIMER, self._onLeituraTick, self.leituraTimer)

		self.ultimoContextoBusca = None
		self.favoritos = self.favoritesManager.all()
		self.favPaginaAtual = 0
		self.favItensPorPagina = 10

		self.lidosLista = []
		self.lidosPaginaAtual = 0
		self.lidosItensPorPagina = 15

		self._ultimoLivroSelecionado = None
		self._ultimoCapituloSelecionado = None

		self._lastVisitedBook = None
		self._lastVisitedChapter = None
		self._precisaBoasVindas = True

		self._navigationStack = []

		self.indexNotasPorLivro = defaultdict(list)
		self._buildNotesIndex()
		self._markedIndices = set()
		self._clipboardInProgress = False
		self._primeira_exibicao = True
		self._txtUpdateTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onTxtUpdateTick, self._txtUpdateTimer)
		self._pendingTxtVerso = None
		self._savePositionTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onSavePositionTick, self._savePositionTimer)

		menuBar = wx.MenuBar()
		menuArquivo = wx.Menu()
		miBuscar = menuArquivo.Append(wx.ID_FIND, "&Buscar na Bíblia\tCtrl+P", "Pesquisar na Bíblia")
		miIrPara = menuArquivo.Append(wx.ID_ANY, "Ir para &referência\tCtrl+R", "Ir diretamente para um livro, capítulo e versículo")
		miCopiar = menuArquivo.Append(wx.ID_COPY, "&Copiar seleção/versículo\tCtrl+C", "Copiar seleção de versículos ou o versículo atual")
		miLimparSelecao = menuArquivo.Append(wx.ID_ANY, "&Limpar seleção\tCtrl+Z", "Remover seleção/marcas")
		menuArquivo.AppendSeparator()
		miAdicionarNota = menuArquivo.Append(wx.ID_ANY, "&Adicionar nota\tCtrl+N", "Adicionar uma nota")
		miRemoverNota = menuArquivo.Append(wx.ID_ANY, "&Remover nota\tCtrl+Del", "Remover a nota selecionada")
		menuArquivo.AppendSeparator()
		miAdicionarFavorito = menuArquivo.Append(wx.ID_ANY, "&Adicionar favorito\tCtrl+F", "Adicionar favorito (em versículos e resultados de busca)")
		miAbrirFavoritos = menuArquivo.Append(wx.ID_ANY, "&Abrir favoritos\tCtrl+Shift+F", "Abrir favoritos (em qualquer janela)")
		miMarcarLido = menuArquivo.Append(wx.ID_ANY, "Marcar/Desmarcar capítulo como lido\tCtrl+M", "Alternar status de leitura do capítulo atual")
		miListarLidos = menuArquivo.Append(wx.ID_ANY, "Listar capítulos lidos\tCtrl+Shift+M", "Exibir histórico de capítulos lidos")
		miGerenciarBiblias = menuArquivo.Append(wx.ID_ANY, "&Gerenciar Bíblias...\tCtrl+G", "Abrir o gerenciador de versões da Bíblia")
		menuArquivo.AppendSeparator()
		miBackup = menuArquivo.Append(wx.ID_ANY, "Backup e Restauração\tCtrl+B", "Salvar ou restaurar configurações do usuário")
		menuArquivo.AppendSeparator()
		miFechar = menuArquivo.Append(wx.ID_EXIT, "&Fechar\tAlt+F4", "Fechar")

		menuNaveg = wx.Menu()
		miVoltar = menuNaveg.Append(wx.ID_BACKWARD, "&Voltar\tEsc", "Voltar")
		miAntCap = menuNaveg.Append(wx.ID_ANY, "Capítulo &Anterior\tLeft", "Capítulo anterior")
		miProxCap = menuNaveg.Append(wx.ID_ANY, "Próximo &Capítulo\tRight", "Próximo capítulo")
		miLeitura = menuNaveg.Append(wx.ID_ANY, "&Leitura contínua (toggle)\tCtrl+L", "Iniciar/Parar leitura contínua")
		miAlternarVersao = menuNaveg.Append(wx.ID_ANY, "&Alternar versão\tCtrl+T", "Alternar para a próxima versão (cíclico)")
		miIndiceLivros = menuNaveg.Append(wx.ID_ANY, "&Índice de livros\tCtrl+I", "Ir para o índice de livros")

		menuExib = wx.Menu()
		miAumentarFonte = menuExib.Append(wx.ID_ANY, "Aumentar fonte\tCtrl++", "Aumentar tamanho da fonte da leitura")
		miDiminuirFonte = menuExib.Append(wx.ID_ANY, "Diminuir fonte\tCtrl+-", "Diminuir tamanho da fonte da leitura")
		self.miTemaEscuro = menuExib.AppendCheckItem(wx.ID_ANY, "Tema escuro", "Alternar tema escuro/claro")
		self.miTemaEscuro.Check(True)
		menuExib.AppendSeparator()
		self.miFalarAoIniciar = menuExib.AppendCheckItem(wx.ID_ANY, "Mostrar versículo ao iniciar", "Lê um versículo aleatório dos seus favoritos ao iniciar o NVDA")
		self.miFalarAoIniciar.Check(self.configManager.get_speak_on_startup())
		self.Bind(wx.EVT_MENU, self._onToggleSpeakOnStartup, self.miFalarAoIniciar)

		menuAjuda = wx.Menu()
		miVisitarSite = menuAjuda.Append(wx.ID_ANY, "&Github", "Abre o repositório do Open Bible no GitHub no navegador")
		miSobre = menuAjuda.Append(wx.ID_ABOUT, "&Sobre", "Sobre Open Bible")

		menuBar.Append(menuArquivo, "&Arquivo")
		menuBar.Append(menuNaveg, "&Navegação")
		menuBar.Append(menuExib, "&Exibição")
		menuBar.Append(menuAjuda, "&Ajuda")
		self.SetMenuBar(menuBar)

		mainPanel = wx.Panel(self)
		mainSizer = wx.BoxSizer(wx.VERTICAL)

		headerSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.lblContexto = wx.StaticText(mainPanel, label="")
		try:
			fontHeader = self.lblContexto.GetFont()
			fontHeader.SetPointSize(fontHeader.GetPointSize() + 4)
			fontHeader.SetWeight(wx.FONTWEIGHT_BOLD)
			self.lblContexto.SetFont(fontHeader)
		except Exception:
			pass
		headerSizer.Add(self.lblContexto, 1, wx.EXPAND | wx.ALL, 8)
		mainSizer.Add(headerSizer, 0, wx.EXPAND)

		navSizer = wx.BoxSizer(wx.HORIZONTAL)

		self._listaCtrl = ListaWrapper(mainPanel, name="Lista de seleção")
		self._listaBox = wx.ListBox(mainPanel, style=wx.LB_SINGLE | wx.LB_ALWAYS_SB, name="Lista de seleção")
		self._listaBox.Hide()
		self.lista = self._listaCtrl
		self._navSizer = navSizer
		navSizer.Add(self._listaCtrl, 1, wx.EXPAND | wx.ALL, 8)
		navSizer.Add(self._listaBox, 1, wx.EXPAND | wx.ALL, 8)

		self.btnSizer = wx.BoxSizer(wx.VERTICAL)
		self.btnAnterior = wx.Button(mainPanel, label="Capítulo Anterior")
		self.btnMarcarLido = wx.Button(mainPanel, label="Marcar capítulo como lido")
		self.btnProximo = wx.Button(mainPanel, label="Próximo Capítulo")
		self.btnLivroAnterior = wx.Button(mainPanel, label="Livro Anterior")
		self.btnProximoLivro = wx.Button(mainPanel, label="Próximo Livro")
		self.btnCopiar = wx.Button(mainPanel, label="Copiar Seleção/Versículo")
		self.btnAdicionarNota = wx.Button(mainPanel, label="Adicionar Nota")
		self.btnRemoverNota = wx.Button(mainPanel, label="Remover Nota")
		self.btnBuscar = wx.Button(mainPanel, label="Buscar na Bíblia")
		self.btnFavoritos = wx.Button(mainPanel, label="Favoritos")
		self.btnPagAnterior = wx.Button(mainPanel, label="Página Anterior")
		self.btnPagProxima = wx.Button(mainPanel, label="Próxima Página")
		self.btnLimparBusca = wx.Button(mainPanel, label="Limpar Busca")

		self.btnSizer.Add(self.btnLivroAnterior, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnAnterior, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnProximo, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnProximoLivro, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnMarcarLido, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnCopiar, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnAdicionarNota, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnRemoverNota, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnBuscar, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnFavoritos, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnPagAnterior, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnPagProxima, 0, wx.EXPAND | wx.ALL, 5)
		self.btnSizer.Add(self.btnLimparBusca, 0, wx.EXPAND | wx.ALL, 5)

		navSizer.Add(self.btnSizer, 0, wx.EXPAND | wx.ALL, 8)
		mainSizer.Add(navSizer, 3, wx.EXPAND)

		self.txtLeitura = wx.TextCtrl(
			mainPanel,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
			name="Área de leitura e contexto"
		)
		self._temaEscuroAtivo = True
		self._aplicarTema(escuro=True)

		try:
			fontRead = self.txtLeitura.GetFont()
			fontRead.SetPointSize(max(18, fontRead.GetPointSize()))
			self.txtLeitura.SetFont(fontRead)
		except Exception:
			pass

		self.txtLeitura.SetInsertionPoint(0)
		mainSizer.Add(self.txtLeitura, 1, wx.EXPAND | wx.ALL, 8)

		mainPanel.SetSizer(mainSizer)

		self._versosLista = []
		self._notasLista = []
		self._temHeaderNotas = False
		self._versosSelecionados = []

		self.Bind(wx.EVT_CHAR_HOOK, self.onChar)
		self._listaCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self.abrir())
		self._listaCtrl.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self._listaCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onListSelectionChanged)
		self._listaBox.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self.abrir())
		self._listaBox.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self._listaBox.Bind(wx.EVT_LISTBOX, self._onListSelectionChanged)
		self.Bind(wx.EVT_CLOSE, self._onCloseSaveLastPosition)

		self.btnAnterior.Bind(wx.EVT_BUTTON, lambda e: self.capituloAnterior())
		self.btnLivroAnterior.Bind(wx.EVT_BUTTON, lambda e: self.livroAnterior())
		self.btnProximoLivro.Bind(wx.EVT_BUTTON, lambda e: self.proximoLivro())
		self.btnMarcarLido.Bind(wx.EVT_BUTTON, lambda e: self.toggleMarcarCapituloLido())
		self.btnProximo.Bind(wx.EVT_BUTTON, lambda e: self.proximoCapitulo())
		self.btnCopiar.Bind(wx.EVT_BUTTON, lambda e: self._copyMarkedOrSelected())
		self.btnAdicionarNota.Bind(wx.EVT_BUTTON, lambda e: self.adicionarNota())
		self.btnRemoverNota.Bind(wx.EVT_BUTTON, lambda e: self.removerNota())
		self.btnBuscar.Bind(wx.EVT_BUTTON, lambda e: self.buscar())
		self.btnFavoritos.Bind(wx.EVT_BUTTON, lambda e: self.mostrarFavoritos())
		self.btnPagAnterior.Bind(wx.EVT_BUTTON, lambda e: self.paginaAnterior() if self.nivel == "busca" else self.paginaFavoritosAnterior())
		self.btnPagProxima.Bind(wx.EVT_BUTTON, lambda e: self.paginaProxima() if self.nivel == "busca" else self.paginaFavoritosProxima())
		self.btnLimparBusca.Bind(wx.EVT_BUTTON, lambda e: self.limparBusca())

		self.Bind(wx.EVT_MENU, lambda e: self.buscar(), miBuscar)
		self.Bind(wx.EVT_MENU, lambda e: self.irParaReferencia(), miIrPara)
		self.Bind(wx.EVT_MENU, lambda e: self._copyMarkedOrSelected(), miCopiar)
		self.Bind(wx.EVT_MENU, lambda e: self._clearMarks_global(), miLimparSelecao)
		self.Bind(wx.EVT_MENU, lambda e: self.adicionarNota(), miAdicionarNota)
		self.Bind(wx.EVT_MENU, lambda e: self.removerNota(), miRemoverNota)
		self.Bind(wx.EVT_MENU, lambda e: self.adicionarFavoritoAtual(), miAdicionarFavorito)
		self.Bind(wx.EVT_MENU, lambda e: self._navToFavoritos(), miAbrirFavoritos)
		self.Bind(wx.EVT_MENU, lambda e: self.toggleMarcarCapituloLido(), miMarcarLido)
		self.Bind(wx.EVT_MENU, lambda e: self._navToLidos(), miListarLidos)
		self.Bind(wx.EVT_MENU, lambda e: self.voltar(), miVoltar)
		self.Bind(wx.EVT_MENU, lambda e: self.capituloAnterior(), miAntCap)
		self.Bind(wx.EVT_MENU, lambda e: self.proximoCapitulo(), miProxCap)
		self.Bind(wx.EVT_MENU, lambda e: self._toggleLeitura(), miLeitura)
		self.Bind(wx.EVT_MENU, lambda e: self._alternarVersaoCiclico(), miAlternarVersao)
		self.Bind(wx.EVT_MENU, lambda e: self.mostrarLivros(), miIndiceLivros)
		self.Bind(wx.EVT_MENU, lambda e: self.abrirDialogoBackup(None), miBackup)
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open("https://github.com/leandro-sds/Open_Bible/"), miVisitarSite)
		self.Bind(wx.EVT_MENU, lambda e: self.sobre(), miSobre)
		self.Bind(wx.EVT_MENU, lambda e: self.Close(), miFechar)
		self.Bind(wx.EVT_MENU, lambda e: self.abrirGerenciadorBiblias(), miGerenciarBiblias)
		self.Bind(wx.EVT_MENU, lambda e: self._ajustarFonte(1), miAumentarFonte)
		self.Bind(wx.EVT_MENU, lambda e: self._ajustarFonte(-1), miDiminuirFonte)
		self.Bind(wx.EVT_MENU, self._onToggleDarkMode, self.miTemaEscuro)

		self.Bind(wx.EVT_SHOW, self._onShowEnsureFocus)
		self.Bind(wx.EVT_ACTIVATE, self._onActivateEnsureFocus)

		accel_tbl = wx.AcceleratorTable([
			(wx.ACCEL_CTRL, ord('P'), miBuscar.GetId()),
			(wx.ACCEL_CTRL, ord('R'), miIrPara.GetId()),
			(wx.ACCEL_CTRL, ord('C'), miCopiar.GetId()),
			(wx.ACCEL_CTRL, ord('N'), miAdicionarNota.GetId()),
			(wx.ACCEL_CTRL, wx.WXK_DELETE, miRemoverNota.GetId()),
			(wx.ACCEL_CTRL, ord('F'), miAdicionarFavorito.GetId()),
			(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('F'), miAbrirFavoritos.GetId()),
			(wx.ACCEL_CTRL, ord('M'), miMarcarLido.GetId()),
			(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('M'), miListarLidos.GetId()),
			(wx.ACCEL_CTRL, ord('G'), miGerenciarBiblias.GetId()),
			(wx.ACCEL_CTRL, ord('B'), miBackup.GetId()),
			(wx.ACCEL_ALT, wx.WXK_F4, miFechar.GetId()),
			(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, miVoltar.GetId()),
		])
		self.SetAcceleratorTable(accel_tbl)

		self._startupWillShowContinuePrompt = False
		try:
			if not self.configManager.get_skip_continue_prompt():
				_livro, _capitulo = self.configManager.get_last_position(self.versaoAtual)
				if _livro and _capitulo:
					self._startupWillShowContinuePrompt = True
		except Exception:
			self._startupWillShowContinuePrompt = False

		self.mostrarLivros(announce=not self._startupWillShowContinuePrompt)
		self.CenterOnScreen()
		self.Show()
		wx.CallAfter(self._ensureListFocus)

		if self.configManager.get_skip_continue_prompt():
			wx.CallLater(200, self._sequenciaBoasVindasSeNecessario)
		else:
			wx.CallAfter(self._promptContinuarLeituraSeExistir)

	def _sequenciaBoasVindasSeNecessario(self):
		if self._precisaBoasVindas and self.nivel == "livros":
			try:
				import speech as sp
				sp.cancelSpeech()
			except Exception:
				pass
			self.anunciar("Selecione um livro")
			self._precisaBoasVindas = False

	def abrirDialogoBackup(self, event):
		self._pararLeituraSeAtiva()
		dlg = wx.MessageDialog(
			self,
			"O que deseja fazer?\n\nCriar Backup: Salva suas configurações, favoritos, notas e histórico.\nRestaurar Backup: Carrega um arquivo salvo anteriormente.",
			"Backup e Restauração",
			wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
		)
		dlg.SetYesNoLabels("Criar Backup", "Restaurar Backup")

		res = dlg.ShowModal()
		dlg.Destroy()

		if res == wx.ID_YES:
			self._realizarBackup()
		elif res == wx.ID_NO:
			self._restaurarBackup()

	def _realizarBackup(self):
		default_name = f"backup_openbible_{datetime.date.today()}.zip"
		fd = wx.FileDialog(
			self, "Salvar Backup",
			wildcard="Arquivo ZIP (*.zip)|*.zip",
			defaultFile=default_name,
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
		)

		if fd.ShowModal() == wx.ID_OK:
			path = fd.GetPath()
			try:
				with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
					for filename in os.listdir(NVDA_CONFIG_BASE):
						if filename.endswith(".json"):
							full_path = os.path.join(NVDA_CONFIG_BASE, filename)
							zf.write(full_path, arcname=filename)
				wx.MessageBox("Backup criado com sucesso!", "Open Bible", wx.OK | wx.ICON_INFORMATION)
			except Exception as e:
				wx.MessageBox(f"Erro ao criar backup: {e}", "Erro", wx.OK | wx.ICON_ERROR)
		fd.Destroy()

	def _restaurarBackup(self):
		fd = wx.FileDialog(
			self, "Selecionar Backup para Restaurar",
			wildcard="Arquivo ZIP (*.zip)|*.zip",
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		)

		if fd.ShowModal() == wx.ID_OK:
			path = fd.GetPath()
			try:
				with zipfile.ZipFile(path, 'r') as zf:
					has_json = any(f.endswith('.json') for f in zf.namelist())
					if not has_json:
						raise ValueError("O arquivo ZIP não parece conter dados do Open Bible.")

					def _safe_extract_backup_zip(zfLocal, destino):
						destinoAbs = os.path.abspath(destino)
						if not _ensure_dir(destinoAbs):
							raise FileNotFoundError("A pasta de configuração do NVDA não foi encontrada. Feche e reabra o NVDA e tente novamente.")
						extraiu = False
						for info in zfLocal.infolist():
							nome = info.filename
							if not isinstance(nome, str) or not nome.lower().endswith(".json"):
								continue
							nome = nome.replace("\\", "/")
							if nome.startswith("/") or re.match(r"^[a-zA-Z]:", nome):
								continue
							partes = [p for p in nome.split("/") if p not in ("", ".")]
							if any(p == ".." for p in partes):
								continue
							base = os.path.basename(nome)
							if not base.lower().endswith(".json"):
								continue
							dest = os.path.abspath(os.path.join(destinoAbs, base))
							if not dest.startswith(destinoAbs + os.sep):
								continue
							os.makedirs(os.path.dirname(dest), exist_ok=True)
							with zfLocal.open(info, "r") as origem, open(dest, "wb") as saida:
								shutil.copyfileobj(origem, saida)
							extraiu = True
						return extraiu

					if not _safe_extract_backup_zip(zf, NVDA_CONFIG_BASE):
						raise ValueError("Nenhum arquivo JSON válido foi encontrado no backup.")

				self.configManager = ConfigManager()
				self.favoritesManager = FavoritesManager()
				self.readManager = ReadChaptersManager()

				versao = self.configManager.get_version()
				if versao and versao in self.bibleManager.listar_nomes():
					try:
						self.biblia = self.bibleManager.carregar(versao)
						self.versaoAtual = versao
					except Exception:
						pass

				self.notesManager = NotesManager(self.versaoAtual)
				self.notas = self.notesManager.all()
				self._buildNotesIndex()
				self.favoritos = self.favoritesManager.all()
				self.lidosLista = self.readManager.all()

				wx.MessageBox("Backup restaurado com sucesso! O Open Bible foi atualizado.", "Open Bible", wx.OK | wx.ICON_INFORMATION)
				self.mostrarLivros()

			except Exception as e:
				wx.MessageBox(f"Erro ao restaurar backup: {e}", "Erro", wx.OK | wx.ICON_ERROR)
		fd.Destroy()

	def _onToggleSpeakOnStartup(self, event):
		estado = self.miFalarAoIniciar.IsChecked()
		self.configManager.set_speak_on_startup(estado)
		msg = "Versículo ao iniciar: Ativado" if estado else "Versículo ao iniciar: Desativado"
		wx.CallLater(150, lambda: self.anunciar(msg))

	def _onToggleDarkMode(self, event):
		is_checked = self.miTemaEscuro.IsChecked()
		self._alternarTema(is_checked)
		msg = "Tema escuro ativado" if is_checked else "Tema claro ativado"
		wx.CallLater(150, lambda: self.anunciar(msg))

	def _aplicarTema(self, escuro=True):
		try:
			if escuro:
				bg = wx.Colour(30, 30, 30)
				fg = wx.Colour(255, 255, 255)
				acc = wx.Colour(45, 45, 45)
			else:
				bg = wx.Colour(245, 245, 245)
				fg = wx.Colour(20, 20, 20)
				acc = wx.Colour(230, 230, 230)

			self.SetBackgroundColour(bg)
			self.lblContexto.SetForegroundColour(fg)
			self.lblContexto.SetBackgroundColour(bg)
			self._listaCtrl.SetBackgroundColour(acc)
			self._listaCtrl.SetForegroundColour(fg)
			self._listaBox.SetBackgroundColour(acc)
			self._listaBox.SetForegroundColour(fg)
			self.txtLeitura.SetBackgroundColour(bg)
			self.txtLeitura.SetForegroundColour(fg)
			self.Refresh()
		except Exception:
			pass

	def _trocarLista(self, usarListBox):
		novo = self._listaBox if usarListBox else self._listaCtrl
		antigo = self._listaCtrl if usarListBox else self._listaBox
		if self.lista is novo:
			return
		self.lista = novo
		antigo.Hide()
		novo.Show()
		self._navSizer.Layout()

	def _alternarTema(self, checked):
		try:
			self._temaEscuroAtivo = checked
			self._aplicarTema(self._temaEscuroAtivo)
		except Exception:
			pass

	def _ajustarFonte(self, delta):
		try:
			font = self.txtLeitura.GetFont()
			newSize = max(10, font.GetPointSize() + delta)
			font.SetPointSize(newSize)
			self.txtLeitura.SetFont(font)
			self.anunciar(f"Fonte tamanho: {newSize}")
		except Exception:
			pass

	def _onTxtUpdateTick(self, event):
		if event.GetTimer() is self._txtUpdateTimer:
			if self._pendingTxtVerso is not None:
				try:
					self.txtLeitura.Freeze()
					self.txtLeitura.SetValue(self._pendingTxtVerso)
					self.txtLeitura.ShowPosition(0)
					self.txtLeitura.Thaw()
				except Exception:
					pass
				self._pendingTxtVerso = None
		else:
			event.Skip()

	def _onSavePositionTick(self, event):
		if event.GetTimer() is self._savePositionTimer:
			try:
				livro = self.livroAtual
				capitulo = self.capituloAtual
				if livro and capitulo:
					self.configManager.set_last_position(self.versaoAtual, livro, capitulo)
			except Exception:
				pass
		else:
			event.Skip()

	def _buildNotesIndex(self):
		self.indexNotasPorLivro.clear()
		self.indexNotasPorLivro = defaultdict(list)
		for n in self.notas:
			if isinstance(n, dict) and {"livro", "capitulo", "nota"} <= set(n.keys()):
				self.indexNotasPorLivro[n["livro"]].append(n)

	def _ensureListFocus(self):
		try:
			if self.lista.GetCount() > 0 and self.lista.GetSelection() == wx.NOT_FOUND:
				self.lista.SetSelection(0)
				self.lista.EnsureVisible(0)
			self.lista.SetFocus()
		except Exception:
			pass

	def _onShowEnsureFocus(self, event):
		event.Skip()
		if self.IsShown():
			wx.CallAfter(self._ensureListFocus)

	def _onActivateEnsureFocus(self, event):
		event.Skip()
		if event.GetActive():
			wx.CallAfter(self._ensureListFocus)

	def anunciar(self, msg):
		if ui:
			try:
				ui.message(msg)
			except Exception:
				pass

	def _atualizarContexto(self, livro=None, capitulo=None):
		nomeLivro = NOMES_LIVROS.get(livro or self.livroAtual, livro or self.livroAtual) or ""
		cap = capitulo if capitulo is not None else self.capituloAtual
		texto = f"{nomeLivro}" + (f" — capítulo {cap}" if cap else "")
		try:
			self.lblContexto.SetLabel(texto)
		except Exception:
			pass

	def sobre(self):
		info = (
			"Open Bible\n"
			"Navegue por livros, capítulos, versículos, busque termos, copie e gerencie notas.\n\n"
			"Pressione F1 para ver a lista de atalhos."
		)
		dlg = wx.MessageDialog(self, info, "Sobre", wx.OK | wx.ICON_INFORMATION)
		dlg.ShowModal()
		dlg.Destroy()

	def _limparSelecao(self):
		self._versosSelecionados = []
		try:
			self.txtLeitura.SetValue("")
		except Exception:
			pass

	def _resetMarksForLevel(self):
		self._markedIndices = set()

	def mostrarAjudaRapida(self):
		dlg = wx.Dialog(self, title="Ajuda rápida – Atalhos", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		vbox = wx.BoxSizer(wx.VERTICAL)

		lbl = wx.StaticText(dlg, label="Navegue com as setas. Esc fecha.")
		vbox.Add(lbl, 0, wx.ALL, 8)

		lc = wx.ListCtrl(dlg, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, name="Lista de atalhos")
		lc.InsertColumn(0, "Atalho")
		lc.InsertColumn(1, "Função")

		atalhos = [
			("Ctrl+Alt+B", "Abrir Open Bible"),
			("Enter/Duplo clique", "Abrir item"),
			("Esc", "Voltar"),
			("Espaço", "Marcar/Desmarcar item"),
			("Ctrl+A", "Marcar todos os itens"),
			("Ctrl+Z", "Limpar seleção/marcas"),
			("Ctrl+C", "Copiar item(s)"),
			("Ctrl+E", "Abrir editor (somente leitura)"),
			("Ctrl+I", "Índice de livros"),
			("Ctrl+L", "Iniciar/Parar leitura contínua"),
			("Esquerda/Direita", "Capítulo anterior/próximo"),
			("Ctrl+Shift+C", "Comparar versículo entre versões"),
			("PageUp/PageDown", "Paginação busca/favoritos"),
			("Ctrl+P", "Buscar na Bíblia"),
			("Ctrl+R", "Ir para referência"),
			("Ctrl+N", "Adicionar nota"),
			("Ctrl+Del", "Remover nota"),
			("Ctrl+F", "Adicionar favorito"),
			("Ctrl+Shift+F", "Abrir favoritos"),
			("Ctrl+M", "Marcar capítulo como lido"),
			("Ctrl+Shift+M", "Listar capítulos lidos"),
			("Ctrl+G", "Gerenciar Bíblias"),
			("Ctrl+B", "Backup e Restauração"),
			("Ctrl+T", "Alternar versão"),
			("Ctrl++", "Aumentar fonte"),
			("Ctrl+-", "Diminuir fonte"),
			("F1", "Abrir esta ajuda rápida"),
			("F5", "Ir para capítulo ou versículo por número"),
		]

		for i, (a, f) in enumerate(atalhos):
			idx = lc.InsertItem(i, a)
			lc.SetItem(idx, 1, f)

		lc.SetColumnWidth(0, 240)
		lc.SetColumnWidth(1, 580)
		vbox.Add(lc, 1, wx.EXPAND | wx.ALL, 8)

		btnClose = wx.Button(dlg, wx.ID_CLOSE, "Fechar")
		vbox.Add(btnClose, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

		dlg.SetSizerAndFit(vbox)
		dlg.CenterOnParent()
		self._bind_global_shortcuts_to_dialog(dlg)
		btnClose.Bind(wx.EVT_BUTTON, lambda e: dlg.Close())

		try:
			if lc.GetItemCount() > 0:
				lc.Focus(0)
				lc.Select(0)
		except Exception:
			pass

		dlg.ShowModal()
		dlg.Destroy()

		try:
			if self.nivel in ("livros", "capitulos", "versiculos", "busca", "favoritos") and self.lista:
				self.lista.SetFocus()
			else:
				self.txtLeitura.SetFocus()
		except Exception:
			pass

	def _confirmarFechamento(self):
		try:
			if self.configManager.get_skip_exit_prompt():
				return True
			dlg = wx.Dialog(self, title="Confirmar fechamento", style=wx.DEFAULT_DIALOG_STYLE)
			vbox = wx.BoxSizer(wx.VERTICAL)
			msg = wx.StaticText(dlg, label="Deseja fechar o Open Bible?")
			vbox.Add(msg, 0, wx.ALL, 10)
			chk = wx.CheckBox(dlg, label="Não lembrar novamente")
			vbox.Add(chk, 0, wx.ALL, 10)
			hbox = wx.BoxSizer(wx.HORIZONTAL)
			btnYes = wx.Button(dlg, wx.ID_YES, "Sim")
			btnNo = wx.Button(dlg, wx.ID_NO, "Não")
			btnYes.SetDefault()
			hbox.Add(btnYes, 0, wx.ALL, 5)
			hbox.Add(btnNo, 0, wx.ALL, 5)
			vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
			dlg.SetSizerAndFit(vbox)
			self._bind_global_shortcuts_to_dialog(dlg)

			def _onYes(e): dlg.EndModal(wx.ID_YES)
			def _onNo(e): dlg.EndModal(wx.ID_NO)
			btnYes.Bind(wx.EVT_BUTTON, _onYes)
			btnNo.Bind(wx.EVT_BUTTON, _onNo)

			res = dlg.ShowModal()
			naoLembrar = chk.GetValue()
			dlg.Destroy()
			if naoLembrar:
				self.configManager.set_skip_exit_prompt(True)
			return res == wx.ID_YES
		except Exception:
			return True

	def _onCloseSaveLastPosition(self, event):
		try:
			if not self._confirmarFechamento():
				event.Veto()
				return
		except Exception:
			pass
		try:
			self._pararLeituraSeAtiva()
			for t in (getattr(self, '_txtUpdateTimer', None), getattr(self, '_savePositionTimer', None)):
				try:
					if t and t.IsRunning():
						t.Stop()
				except Exception:
					pass
			livro = self.livroAtual or getattr(self, "_lastVisitedBook", None)
			capitulo = self.capituloAtual or getattr(self, "_lastVisitedChapter", None)
			if livro and capitulo:
				self.configManager.set_last_position(self.versaoAtual, livro, capitulo)
		except Exception:
			pass
		event.Skip()

	def _bind_global_shortcuts_to_dialog(self, dlg):
		def _dialogCharHook(evt):
			keyCode = evt.GetKeyCode()
			ctrl = evt.ControlDown()
			shift = evt.ShiftDown()
			alt = evt.AltDown()

			if ctrl and not shift and not alt and keyCode == ord('F'):
				try:
					self._push_navigation_state()
					self.mostrarFavoritos()
				finally:
					try:
						dlg.EndModal(wx.ID_CANCEL)
					except Exception:
						dlg.Close()
				return
			if ctrl and not shift and not alt and keyCode == ord('I'):
				try:
					self.mostrarLivros()
				finally:
					try:
						dlg.EndModal(wx.ID_CANCEL)
					except Exception:
						dlg.Close()
				return
			if keyCode == wx.WXK_F1:
				try:
					self.mostrarAjudaRapida()
				except Exception:
					pass
				return
			if keyCode == wx.WXK_ESCAPE:
				try:
					dlg.EndModal(wx.ID_CANCEL)
				except Exception:
					dlg.Close()
				return
			evt.Skip()
		try:
			dlg.Bind(wx.EVT_CHAR_HOOK, _dialogCharHook)
		except Exception:
			pass

	def _promptContinuarLeituraSeExistir(self):
		try:
			if not self.versaoAtual:
				self.mostrarLivros()
				return
			livro, capitulo = self.configManager.get_last_position(self.versaoAtual)
			if self.configManager.get_skip_continue_prompt():
				self.mostrarLivros()
				if not livro or not capitulo:
					self._sequenciaBoasVindasSeNecessario()
				return

			if livro and capitulo:
				self._precisaBoasVindas = False

				nomeLivro = NOMES_LIVROS.get(livro, livro)
				dlg = wx.Dialog(self, title="Continuar leitura", style=wx.DEFAULT_DIALOG_STYLE)
				vbox = wx.BoxSizer(wx.VERTICAL)
				msg = wx.StaticText(dlg, label=f"Deseja continuar a leitura em '{nomeLivro}' - 'Capítulo {capitulo}'?")
				vbox.Add(msg, 0, wx.ALL, 10)
				chk = wx.CheckBox(dlg, label="Não mostrar novamente")
				vbox.Add(chk, 0, wx.ALL, 10)
				hbox = wx.BoxSizer(wx.HORIZONTAL)
				btnYes = wx.Button(dlg, wx.ID_YES, "Sim")
				btnNo = wx.Button(dlg, wx.ID_NO, "Não")
				btnYes.SetDefault()
				hbox.Add(btnYes, 0, wx.ALL, 5)
				hbox.Add(btnNo, 0, wx.ALL, 5)
				vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
				dlg.SetSizerAndFit(vbox)
				self._bind_global_shortcuts_to_dialog(dlg)
				def _onYes(e): dlg.EndModal(wx.ID_YES)
				def _onNo(e): dlg.EndModal(wx.ID_NO)
				btnYes.Bind(wx.EVT_BUTTON, _onYes)
				btnNo.Bind(wx.EVT_BUTTON, _onNo)

				res = dlg.ShowModal()
				naoMostrar = chk.GetValue()
				dlg.Destroy()
				if naoMostrar:
					self.configManager.set_skip_continue_prompt(True)
				if res == wx.ID_YES:
					self._ultimoLivroSelecionado = livro
					self._ultimoCapituloSelecionado = capitulo
					self.mostrarVersiculos(livro, capitulo)
					try:
						if self._versosLista:
							self.lista.SetSelection(0)
							self.lista.SetFocus()
						self.leituraIndice = 0
					except Exception:
						pass
					self.anunciar(f"Continuando em {nomeLivro}, capítulo {capitulo}")
				else:
					self.mostrarLivros()
			else:
				self.mostrarLivros()
				self._sequenciaBoasVindasSeNecessario()
		except Exception:
			self.mostrarLivros()
			self._sequenciaBoasVindasSeNecessario()

	def _push_navigation_state(self):
		state = {
			"nivel": self.nivel,
			"livro": self.livroAtual,
			"capitulo": self.capituloAtual,
			"versao": self.versaoAtual,
			"selecao_index": self.lista.GetSelection(),
			"resultadosBusca": self.resultadosBusca if self.nivel == "busca" else None,
			"paginaAtual": self.paginaAtual if self.nivel == "busca" else None,
			"ultimoContextoBusca": self.ultimoContextoBusca
		}
		self._navigationStack.append(state)

	def _restore_navigation_state(self):
		if not self._navigationStack:
			return False

		state = self._navigationStack.pop()
		nivel = state.get("nivel")

		if nivel == "versiculos":
			self.mostrarVersiculos(state["livro"], state["capitulo"])
			try:
				if state["selecao_index"] != wx.NOT_FOUND:
					self.lista.SetSelection(state["selecao_index"])
					wx.CallAfter(self._ensureListFocus)
			except Exception:
				pass
			return True

		if nivel == "livros":
			self.mostrarLivros()
			try:
				if state["selecao_index"] != wx.NOT_FOUND:
					self.lista.SetSelection(state["selecao_index"])
					wx.CallAfter(self._ensureListFocus)
			except Exception:
				pass
			return True

		if nivel == "capitulos":
			self.mostrarCapitulos(state["livro"])
			try:
				if state["selecao_index"] != wx.NOT_FOUND:
					self.lista.SetSelection(state["selecao_index"])
					wx.CallAfter(self._ensureListFocus)
			except Exception:
				pass
			return True

		if nivel == "busca":
			self.resultadosBusca = state.get("resultadosBusca", [])
			self.paginaAtual = state.get("paginaAtual", 0)
			self.ultimoContextoBusca = state.get("ultimoContextoBusca")
			self.mostrarResultadosBusca()
			try:
				if state["selecao_index"] != wx.NOT_FOUND:
					self.lista.SetSelection(state["selecao_index"])
					wx.CallAfter(self._ensureListFocus)
			except Exception:
				pass
			return True

		if nivel == "lidos":
			self.mostrarCapitulosLidos()
			try:
				if state["selecao_index"] != wx.NOT_FOUND:
					self.lista.SetSelection(state["selecao_index"])
					wx.CallAfter(self._ensureListFocus)
			except Exception:
				pass
			return True

		if nivel == "favoritos":
			self.mostrarFavoritos()
			try:
				if state["selecao_index"] != wx.NOT_FOUND:
					self.lista.SetSelection(state["selecao_index"])
					wx.CallAfter(self._ensureListFocus)
			except Exception:
				pass
			return True

		return False

	def _updateVisibleButtons(self, visible_buttons):
		all_buttons = [
			self.btnLivroAnterior, self.btnAnterior, self.btnMarcarLido, self.btnProximo, self.btnProximoLivro,
			self.btnCopiar, self.btnAdicionarNota, self.btnRemoverNota, self.btnBuscar,
			self.btnFavoritos, self.btnPagAnterior, self.btnPagProxima,
			self.btnLimparBusca
		]

		for btn in all_buttons:
			btn.Hide()

		for btn in visible_buttons:
			btn.Show()

		self.btnSizer.Layout()

	def mostrarLivros(self, announce=True):
		self._pararLeituraSeAtiva()
		self._navigationStack.clear()
		self.nivel = "livros"
		self._trocarLista(usarListBox=False)
		self.livroAtual = None
		self.capituloAtual = None
		self._limparSelecao()
		self._resetMarksForLevel()
		livros_siglas = [sigla for sigla in NOMES_LIVROS if self.bibleManager.bible_tree.get(sigla)]
		self.livrosSiglas = livros_siglas
		nomes = [NOMES_LIVROS[s] for s in livros_siglas]
		self.lista.Freeze()
		self.lista.Clear()
		if nomes:
			self.lista.AppendItems(nomes)
		self.lista.Thaw()
		if nomes:
			if self._ultimoLivroSelecionado and self._ultimoLivroSelecionado in livros_siglas:
				try:
					idx = livros_siglas.index(self._ultimoLivroSelecionado)
					self.lista.SetSelection(idx)
				except Exception:
					self.lista.SetSelection(0)
			else:
				self.lista.SetSelection(0)
		else:
			self.lista.SetSelection(wx.NOT_FOUND)
		self._updateButtonsForLevel()
		try:
			self.btnCopiar.Disable()
		except Exception:
			pass
		self.SetTitle("Open Bible" + (f" – {self.versaoAtual}" if self.versaoAtual else ""))
		self._atualizarContexto(livro=None, capitulo=None)
		wx.CallAfter(self._ensureListFocus)
		self.leituraIndice = 0
		self._leituraTotalVersos = 0

		self.txtLeitura.SetValue("Open Bible\n\nSelecione um livro.")

		if announce:
			if getattr(self, "_primeira_exibicao", True):
				wx.CallLater(600, lambda: self.anunciar("Selecione um livro"))
				self._primeira_exibicao = False
			else:
				self.anunciar("Selecione um livro")

	def mostrarCapitulos(self, livro):
		self._pararLeituraSeAtiva()
		self.nivel = "capitulos"
		self._trocarLista(usarListBox=True)
		self._limparSelecao()
		self._resetMarksForLevel()
		self.livroAtual = livro
		caps_data = self.bibleManager.bible_tree.get(livro, {})
		caps = sorted(caps_data.keys())
		self.capitulos = caps
		self.lista.Freeze()
		self.lista.Clear()
		if caps:
			self.lista.AppendItems([str(c) for c in caps])
		self.lista.Thaw()
		if caps:
			if self._ultimoCapituloSelecionado and self._ultimoCapituloSelecionado in caps:
				try:
					idx = caps.index(self._ultimoCapituloSelecionado)
					self.lista.SetSelection(idx)
				except Exception:
					self.lista.SetSelection(0)
			else:
				self.lista.SetSelection(0)
		else:
			self.lista.SetSelection(wx.NOT_FOUND)
		self._updateButtonsForLevel()
		nomeLivro = NOMES_LIVROS.get(livro, livro)
		self.SetTitle("Open Bible" + (f" – {self.versaoAtual}" if self.versaoAtual else "") + f" – {nomeLivro}")
		self._atualizarContexto(livro=livro, capitulo=None)
		wx.CallAfter(self._ensureListFocus)
		self.leituraIndice = 0
		self._leituraTotalVersos = 0
		self.txtLeitura.SetValue(f"{nomeLivro}\nSelecione um capítulo.")
		self.anunciar("Selecione um capítulo")

	def _marcadorSelecao(self, versoNum):
		return f"✓{versoNum}"

	def _formatVersoLine(self, v, marcado=False):
		prefixoSel = (self._marcadorSelecao(v['versiculo']) + " ") if marcado else ""
		return f"{prefixoSel}{v['versiculo']}: {v['texto']}"

	def _renderLeituraCapitulo(self, livro, capitulo, linhas_versos, notasCap):
		try:
			self.txtLeitura.Freeze()
			cab = NOMES_LIVROS.get(livro, livro) + f" {capitulo}\n\n"

			partes_texto = [cab]
			partes_texto.extend(linhas_versos)

			if notasCap:
				partes_texto.append("\n---- Anotações ----")
				for n in notasCap:
					if "versiculo" in n:
						partes_texto.append(f"Nota {n['versiculo']}: {n['nota']}")
					else:
						partes_texto.append(f"Nota capítulo {capitulo}: {n['nota']}")

			texto_completo = "\n".join(partes_texto)
			self.txtLeitura.SetValue(texto_completo)
			self.txtLeitura.ShowPosition(0)
		finally:
			try:
				self.txtLeitura.Thaw()
			except Exception:
				pass

	def toggleMarcarCapituloLido(self):
		if self.nivel != "versiculos" or not self.livroAtual or not self.capituloAtual:
			self.anunciar("Abra um capítulo para marcar como lido.")
			return

		is_read = self.readManager.is_read(self.livroAtual, self.capituloAtual)
		if is_read:
			self.readManager.remove(self.livroAtual, self.capituloAtual)
			self.btnMarcarLido.SetLabel("Marcar capítulo como lido")
			self.anunciar("Capítulo desmarcado como lido")
		else:
			self.readManager.mark_read(self.livroAtual, self.capituloAtual)
			self.btnMarcarLido.SetLabel("Desmarcar capítulo como lido")
			self.anunciar("Capítulo marcado como lido")

	def mostrarVersiculos(self, livro, capitulo):
		self._pararLeituraSeAtiva()
		self.nivel = "versiculos"
		self._trocarLista(usarListBox=True)
		self._resetMarksForLevel()
		self.livroAtual = livro
		self.capituloAtual = capitulo

		try:
			self._lastVisitedBook = livro
			self._lastVisitedChapter = capitulo
			if self._savePositionTimer.IsRunning():
				self._savePositionTimer.Stop()
			self._savePositionTimer.Start(800, oneShot=True)
		except Exception:
			pass

		is_read = self.readManager.is_read(livro, capitulo)
		self.btnMarcarLido.SetLabel("Desmarcar capítulo como lido" if is_read else "Marcar capítulo como lido")

		caps_data = self.bibleManager.bible_tree.get(livro, {})
		self.capitulos = sorted(caps_data.keys())

		versos = caps_data.get(capitulo, [])
		self._versosSelecionados = [v for v in self._versosSelecionados if v in versos]

		linhas = [self._formatVersoLine(v, any(s is v for s in self._versosSelecionados)) for v in versos]

		notasCap = [n for n in self.indexNotasPorLivro.get(livro, []) if n["capitulo"] == capitulo]

		self._versosLista = versos
		self._notasLista = notasCap
		self._temHeaderNotas = bool(notasCap)
		self._leituraTotalVersos = len(self._versosLista)

		self.lista.Freeze()
		self.lista.Clear()
		if linhas:
			self.lista.AppendItems(linhas)
		if notasCap:
			self.lista.Append("---- Anotações ----")
			for n in notasCap:
				if "versiculo" in n:
					linha = f"Nota {n['versiculo']}: {n['nota']}"
				else:
					linha = f"Nota capítulo {capitulo}: {n['nota']}"
				self.lista.Append(linha)
		self.lista.Thaw()

		if linhas:
			self.lista.SetSelection(0)
			self.lista.SetFocus()
		else:
			self.lista.SetSelection(wx.NOT_FOUND)

		nomeLivro = NOMES_LIVROS.get(livro, livro)
		self.SetTitle("Open Bible" + (f" – {self.versaoAtual}" if self.versaoAtual else "") + f" – {nomeLivro} {capitulo}")
		self._updateButtonsForChapter()
		wx.CallAfter(self._ensureListFocus)
		self._atualizarContexto(livro=livro, capitulo=capitulo)

		self._renderLeituraCapitulo(livro, capitulo, linhas, notasCap)

		self.leituraIndice = 0
		self.anunciar(f"{nomeLivro}, capítulo {capitulo}")

	def abrir(self):
		idx = self.lista.GetSelection()
		if idx == wx.NOT_FOUND:
			return

		if self.nivel == "livros":
			livro = self.livrosSiglas[idx]
			self._ultimoLivroSelecionado = livro
			self._ultimoCapituloSelecionado = None
			self.mostrarCapitulos(livro)
			return

		if self.nivel == "capitulos":
			cap = int(self.lista.GetString(idx))
			self._ultimoCapituloSelecionado = cap
			self.mostrarVersiculos(self.livroAtual, cap)
			return

		if self.nivel == "versiculos":
			numVersos = len(self._versosLista)
			if idx < numVersos:
				texto = self.lista.GetString(idx)
				self.anunciar(texto)
				return

			if self._temHeaderNotas and idx == numVersos:
				self.anunciar("Anotações")
				return

			notaIndexBase = numVersos + (1 if self._temHeaderNotas else 0)
			notaIdx = idx - notaIndexBase
			if 0 <= notaIdx < len(self._notasLista):
				nota = self._notasLista[notaIdx]
				if "versiculo" in nota:
					versoNum = int(nota["versiculo"])
					try:
						pos = [v["versiculo"] for v in self._versosLista].index(versoNum)
						self.lista.SetSelection(pos)
						self.lista.SetFocus()
						texto = self.lista.GetString(pos)
						self.anunciar(texto)
					except Exception:
						msgNota = f"Nota {versoNum}: {nota['nota']}"
						self.anunciar(msgNota)
				else:
					msgNota = f"Nota capítulo {self.capituloAtual}: {nota['nota']}"
					self.anunciar(msgNota)
				return

			texto = self.lista.GetString(idx)
			self.anunciar(texto)
			return

		if self.nivel == "busca":
			inicio = self.paginaAtual * self.itensPorPagina
			v = self.resultadosBusca[inicio + idx]
			self._ultimoLivroSelecionado = v["livro"]
			self._ultimoCapituloSelecionado = v["capitulo"]
			self._navigationStack = [s for s in self._navigationStack if s["nivel"] != "busca"]
			self.mostrarVersiculos(v["livro"], v["capitulo"])
			try:
				versos_cap = self.bibleManager.bible_tree[v["livro"]][v["capitulo"]]
				pos = [vv["versiculo"] for vv in versos_cap].index(v["versiculo"])
				self.lista.SetSelection(pos)
				self.lista.SetFocus()
				nomeLivro = NOMES_LIVROS.get(v["livro"], v["livro"])
				self.anunciar(f"{nomeLivro}, capítulo {v['capitulo']}")
				versoLinha = f"{v['versiculo']}: {v['texto']}"
				self.anunciar(versoLinha)
			except Exception:
				pass
			self.ultimoContextoBusca = {
				"resultados": self.resultadosBusca,
				"pagina": self.paginaAtual,
				"termo": getattr(self, "_ultimoTermoBusca", None),
				"filtroLivro": getattr(self, "_ultimoFiltroLivro", None),
			}
			return

		if self.nivel == "favoritos":
			inicio = self.favPaginaAtual * self.favItensPorPagina
			realIdx = inicio + idx
			if 0 <= realIdx < len(self.favoritos):
				fav = self.favoritos[realIdx]
				self._ultimoLivroSelecionado = fav["livro"]
				self._ultimoCapituloSelecionado = fav["capitulo"]
				self._navigationStack = [s for s in self._navigationStack if s["nivel"] != "favoritos"]
				self.mostrarVersiculos(fav["livro"], fav["capitulo"])
				try:
					versos_cap = self.bibleManager.bible_tree[fav["livro"]][fav["capitulo"]]
					pos = [vv["versiculo"] for vv in versos_cap].index(fav["versiculo"])
					self.lista.SetSelection(pos)
					self.lista.SetFocus()
					nomeLivro = NOMES_LIVROS.get(fav["livro"], fav["livro"])
					self.anunciar(f"{nomeLivro}, capítulo {fav['capitulo']}")
					versoLinha = f"{fav['versiculo']}: {fav['texto']}"
					self.anunciar(versoLinha)
				except Exception:
					pass
			return

		if self.nivel == "lidos":
			inicio = self.lidosPaginaAtual * self.lidosItensPorPagina
			realIdx = inicio + idx
			if 0 <= realIdx < len(self.lidosLista):
				item = self.lidosLista[realIdx]
				self._ultimoLivroSelecionado = item["livro"]
				self._ultimoCapituloSelecionado = item["capitulo"]
				self._push_navigation_state()
				self.mostrarVersiculos(item["livro"], item["capitulo"])
			return

	def abrirEditorTexto(self):
		self._pararLeituraSeAtiva()
		idx = self.lista.GetSelection()
		if idx == wx.NOT_FOUND:
			return

		texto_exibir = ""
		titulo = "Editor de Versículo"

		if self.nivel == "versiculos":
			if idx < len(self._versosLista):
				v = self._versosLista[idx]
				livroNome = NOMES_LIVROS.get(self.livroAtual, self.livroAtual)
				titulo = f"{livroNome} {self.capituloAtual}:{v['versiculo']}"
				texto_exibir = v['texto']
			else:
				return
		elif self.nivel == "busca":
			inicio = self.paginaAtual * self.itensPorPagina
			realIdx = inicio + idx
			if 0 <= realIdx < len(self.resultadosBusca):
				v = self.resultadosBusca[realIdx]
				livroNome = NOMES_LIVROS.get(v['livro'], v['livro'])
				titulo = f"{livroNome} {v['capitulo']}:{v['versiculo']}"
				texto_exibir = v['texto']
			else:
				return
		elif self.nivel == "favoritos":
			inicio = self.favPaginaAtual * self.favItensPorPagina
			realIdx = inicio + idx
			if 0 <= realIdx < len(self.favoritos):
				fav = self.favoritos[realIdx]
				livroNome = NOMES_LIVROS.get(fav["livro"], fav["livro"])
				titulo = f"{livroNome} {fav['capitulo']}:{fav['versiculo']}"
				texto_exibir = fav['texto']
			else:
				return
		else:
			return

		dlg = wx.Dialog(self, title=titulo, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		vbox = wx.BoxSizer(wx.VERTICAL)

		txtEditor = wx.TextCtrl(dlg, value=texto_exibir, style=wx.TE_MULTILINE | wx.TE_READONLY, name="Texto do versículo")
		try:
			f = txtEditor.GetFont()
			f.SetPointSize(16)
			txtEditor.SetFont(f)
		except Exception:
			pass

		vbox.Add(txtEditor, 1, wx.EXPAND | wx.ALL, 10)

		btnFechar = wx.Button(dlg, wx.ID_CLOSE, "Fechar")
		vbox.Add(btnFechar, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

		dlg.SetSizer(vbox)
		dlg.SetSize((600, 400))
		dlg.CenterOnParent()

		btnFechar.Bind(wx.EVT_BUTTON, lambda e: dlg.Close())

		def _onEditorChar(evt):
			if evt.GetKeyCode() == wx.WXK_ESCAPE:
				dlg.Close()
			else:
				evt.Skip()
		txtEditor.Bind(wx.EVT_CHAR_HOOK, _onEditorChar)

		dlg.ShowModal()
		dlg.Destroy()
		self.lista.SetFocus()

	def voltar(self):
		self._pararLeituraSeAtiva()

		if self._restore_navigation_state():
			return

		if self.nivel == "versiculos":
			self._ultimoCapituloSelecionado = self.capituloAtual
			self.mostrarCapitulos(self.livroAtual)
		elif self.nivel == "capitulos":
			self._ultimoLivroSelecionado = self.livroAtual
			self.mostrarLivros()
		elif self.nivel in ("busca", "favoritos", "lidos"):
			self.mostrarLivros()
		else:
			self.Close()

	def capituloAnterior(self):
		self._pararLeituraSeAtiva()
		if self.nivel == "versiculos" and self.capituloAtual is not None and self.capitulos:
			try:
				idx = self.capitulos.index(self.capituloAtual)
				if idx > 0:
					novoCap = self.capitulos[idx - 1]
					self._ultimoCapituloSelecionado = novoCap
					self.mostrarVersiculos(self.livroAtual, novoCap)
			except (ValueError, Exception):
				pass

	def proximoCapitulo(self):
		self._pararLeituraSeAtiva()
		if self.nivel == "versiculos" and self.capituloAtual is not None and self.capitulos:
			try:
				idx = self.capitulos.index(self.capituloAtual)
				if idx < len(self.capitulos) - 1:
					novoCap = self.capitulos[idx + 1]
					self._ultimoCapituloSelecionado = novoCap
					self.mostrarVersiculos(self.livroAtual, novoCap)
			except (ValueError, Exception):
				pass

	def livroAnterior(self):
		self._pararLeituraSeAtiva()
		if self.nivel != "versiculos" or not self.livroAtual:
			return
		livrosSiglas = [s for s in NOMES_LIVROS if self.bibleManager.bible_tree.get(s)]
		try:
			idx = livrosSiglas.index(self.livroAtual)
			if idx > 0:
				novoLivro = livrosSiglas[idx - 1]
				caps = sorted(self.bibleManager.bible_tree[novoLivro].keys())
				ultimoCap = caps[-1]
				self._ultimoLivroSelecionado = novoLivro
				self._ultimoCapituloSelecionado = ultimoCap
				self.mostrarVersiculos(novoLivro, ultimoCap)
				nomeLivro = NOMES_LIVROS.get(novoLivro, novoLivro)
				self.anunciar(f"{nomeLivro}, capítulo {ultimoCap}")
		except (ValueError, Exception):
			pass

	def proximoLivro(self):
		self._pararLeituraSeAtiva()
		if self.nivel != "versiculos" or not self.livroAtual:
			return
		livrosSiglas = [s for s in NOMES_LIVROS if self.bibleManager.bible_tree.get(s)]
		try:
			idx = livrosSiglas.index(self.livroAtual)
			if idx < len(livrosSiglas) - 1:
				novoLivro = livrosSiglas[idx + 1]
				caps = sorted(self.bibleManager.bible_tree[novoLivro].keys())
				primeiroCap = caps[0]
				self._ultimoLivroSelecionado = novoLivro
				self._ultimoCapituloSelecionado = primeiroCap
				self.mostrarVersiculos(novoLivro, primeiroCap)
				nomeLivro = NOMES_LIVROS.get(novoLivro, novoLivro)
				self.anunciar(f"{nomeLivro}, capítulo {primeiroCap}")
		except (ValueError, Exception):
			pass

	def _calcIntervalo(self, texto: str) -> int:
		base = 250
		porChar = 12
		tempo = base + len(texto) * porChar
		return max(500, min(5000, tempo))

	def _toggleLeitura(self):
		if self.nivel != "versiculos":
			self.anunciar("Abra um capítulo para iniciar a leitura contínua")
			return
		if self.leituraAtiva:
			self._pararLeituraSeAtiva()
			self.anunciar("Leitura interrompida")
		else:
			self._iniciarLeituraContinua()

	def _iniciarLeituraContinua(self):
		total_versos = self._leituraTotalVersos or len(self._versosLista)
		if total_versos <= 0:
			return

		sel = self.lista.GetSelection()
		if sel != wx.NOT_FOUND and sel < total_versos:
			self.leituraIndice = sel

		if self.leituraIndice >= total_versos:
			self.leituraIndice = 0

		self.leituraAtiva = True
		self.anunciar("Leitura contínua iniciada")

		self._falarECalcularProximo()

	def _pararLeituraSeAtiva(self):
		try:
			if self.leituraTimer.IsRunning():
				self.leituraTimer.Stop()
		except Exception:
			pass
		self.leituraAtiva = False

	def _falarECalcularProximo(self):
		if not self.leituraAtiva:
			return

		total_versos = self._leituraTotalVersos or len(self._versosLista)
		if self.leituraIndice >= total_versos:
			self._pararLeituraSeAtiva()
			self.anunciar("Fim do capítulo")
			return

		try:
			self.lista.SetSelection(self.leituraIndice)
			self.lista.SetFocus()
			texto = self.lista.GetString(self.leituraIndice)
			self.anunciar(texto)

			tempoEspera = self._calcIntervalo(texto)
			self.leituraTimer.Start(tempoEspera, oneShot=True)

		except Exception:
			self._pararLeituraSeAtiva()

	def _onLeituraTick(self, event):
		if not self.leituraAtiva:
			self._pararLeituraSeAtiva()
			return

		self.leituraIndice += 1
		self._falarECalcularProximo()

	def _strip_prefix(self, s: str) -> str:
		return s.lstrip(" ✓")

	def _toggleMarkCurrentItem(self):
		if self.nivel == "livros":
			if ui:
				ui.message("Seleção não disponível no índice de livros.")
			return
		idx = self.lista.GetSelection()
		if idx == wx.NOT_FOUND:
			return

		if self.nivel == "versiculos":
			if idx < len(self._versosLista):
				v = self._versosLista[idx]
				marcado = any(s is v for s in self._versosSelecionados)
				if marcado:
					self._versosSelecionados = [s for s in self._versosSelecionados if s is not v]
					self.anunciar(f"Versículo {v['versiculo']} desmarcado")
				else:
					self._versosSelecionados.append(v)
					self.anunciar(f"Versículo {v['versiculo']} selecionado")
				try:
					self.lista.SetString(idx, self._formatVersoLine(v, not marcado))
				except Exception:
					pass
			return

		if idx in self._markedIndices:
			self._markedIndices.remove(idx)
			self.anunciar("Item desmarcado")
		else:
			self._markedIndices.add(idx)
			self.anunciar("Item marcado")
		self._refreshListWithMarks(incrementalIndex=idx)

	def _markAllCurrent(self):
		if self.nivel == "livros":
			if ui:
				ui.message("Seleção não disponível no índice de livros.")
			return
		if self.nivel == "versiculos":
			self._versosSelecionados = list(self._versosLista)
			try:
				for i, v in enumerate(self._versosLista):
					self.lista.SetString(i, self._formatVersoLine(v, True))
				self.lista.SetSelection(0)
				self.lista.SetFocus()
			except Exception:
				pass
			self.anunciar("Todos os versículos do capítulo selecionados")
			return
		count = self.lista.GetCount()
		self._markedIndices = set(range(count))
		self._refreshListWithMarks()
		self.anunciar("Todos os itens selecionados")

	def _clearMarks_global(self):
		if self.nivel == "livros":
			if ui:
				ui.message("Seleção não disponível no índice de livros.")
			return
		if self.nivel == "versiculos":
			try:
				for i, v in enumerate(self._versosLista):
					self.lista.SetString(i, self._formatVersoLine(v, False))
			except Exception:
				pass
			self._limparSelecao()
			self.anunciar("Seleção de versículos limpa")
			return
		self._markedIndices = set()
		self._refreshListWithMarks()
		self.anunciar("Seleção limpa")

	def _refreshListWithMarks(self, incrementalIndex=None):
		if self.nivel in ("busca", "favoritos", "capitulos"):
			try:
				self.lista.Freeze()
			except Exception:
				pass
			try:
				if incrementalIndex is not None:
					try:
						s = self._strip_prefix(self.lista.GetString(incrementalIndex))
						prefix = "✓ " if incrementalIndex in self._markedIndices else ""
						self.lista.SetString(incrementalIndex, f"{prefix}{s}")
					except Exception:
						pass
				else:
					try:
						count = self.lista.GetCount()
						for i in range(count):
							s = self._strip_prefix(self.lista.GetString(i))
							prefix = "✓ " if i in self._markedIndices else ""
							self.lista.SetString(i, f"{prefix}{s}")
					except Exception:
						pass
			finally:
				try:
					self.lista.Thaw()
				except Exception:
					pass

	def _copyTextAsync(self, textoCopiar: str, onDone=None):
		if self._clipboardInProgress:
			return

		textoSeg = textoCopiar if isinstance(textoCopiar, str) else str(textoCopiar)
		self._clipboardInProgress = True

		try:
			hwndOwner = self.GetHandle()
		except Exception:
			hwndOwner = 0

		def finalizar(ok: bool):
			self._clipboardInProgress = False
			try:
				if ok:
					if onDone:
						onDone()
				else:
					if ui:
						ui.message("Não foi possível acessar a área de transferência.")
			except Exception:
				pass

		def tentarWxClipboard():
			try:
				if wx.TheClipboard.Open():
					try:
						wx.TheClipboard.SetData(wx.TextDataObject(textoSeg))
						try:
							wx.TheClipboard.Flush()
						except Exception:
							pass
						wx.TheClipboard.Close()
						wx.CallLater(10, finalizar, True)
						return True
					except Exception:
						try:
							wx.TheClipboard.Close()
						except Exception:
							pass
			except Exception:
				pass
			return False

		def tentarWin32UmaVez():
			try:
				if win32clipboard and win32con:
					win32clipboard.OpenClipboard(hwndOwner)
					try:
						win32clipboard.EmptyClipboard()
						win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, textoSeg)
						win32clipboard.CloseClipboard()
						wx.CallLater(10, finalizar, True)
						return True
					except Exception:
						try:
							win32clipboard.CloseClipboard()
						except Exception:
							pass
			except Exception:
				pass
			return False

		def tentarWin32ComRetentativa(tentativa=0, maxTentativas=8):
			if tentarWin32UmaVez():
				return
			if tentativa < maxTentativas - 1:
				wx.CallLater(25, tentarWin32ComRetentativa, tentativa + 1, maxTentativas)
			else:
				wx.CallLater(10, finalizar, False)

		if tentarWxClipboard():
			return
		tentarWin32ComRetentativa()

	def _copyMarkedOrSelected(self):
		textoCopiar = ""
		ref = ""
		copiedCount = 0
		if self.nivel == "versiculos":
			idx = self.lista.GetSelection()
			def ref_str_interval_or_list(livroNome, cap, vers_list):
				vs = sorted(set(int(v) for v in vers_list))
				ranges = []
				start = None
				prev = None
				for num in vs:
					if start is None:
						start = num
						prev = num
					elif num == prev + 1:
						prev = num
					else:
						ranges.append((start, prev))
						start = num
						prev = num
				if start is not None:
					ranges.append((start, prev))
				parts = []
				for s, e in ranges:
					if s == e:
						parts.append(str(s))
					else:
						parts.append(f"{s}-{e}")
				return f"{livroNome} {cap}:{','.join(parts)}"
			if self._versosSelecionados:
				selecionados = sorted(self._versosSelecionados, key=lambda x: x["versiculo"])
				textos = [f"{v['texto']}" for v in selecionados]
				numeros = [v['versiculo'] for v in selecionados]
				livroNome = NOMES_LIVROS.get(self.livroAtual, self.livroAtual)
				ref = ref_str_interval_or_list(livroNome, self.capituloAtual, numeros)
				textoCopiar = "\n".join(textos) + "\n" + ref
				copiedCount = len(selecionados)
			else:
				if idx == wx.NOT_FOUND or idx >= len(self._versosLista):
					if ui:
						ui.message("Selecione um versículo para copiar")
					return
				v = self._versosSelecionados[0] if self._versosSelecionados else self._versosLista[idx]
				livroNome = NOMES_LIVROS.get(self.livroAtual, self.livroAtual)
				ref = f"{livroNome} {self.capituloAtual}:{v['versiculo']}"
				textoCopiar = f"{v['texto']} - {ref}"
				copiedCount = 1
		elif self.nivel == "busca":
			indices = list(self._markedIndices)
			if not indices:
				sel = self.lista.GetSelection()
				if sel != wx.NOT_FOUND:
					indices = [sel]
			inicio = self.paginaAtual * self.itensPorPagina
			linhas = []
			for i in indices:
				realIdx = inicio + i
				if 0 <= realIdx < len(self.resultadosBusca):
					v = self.resultadosBusca[realIdx]
					ref_line = f"{NOMES_LIVROS.get(v['livro'], v['livro'])} {v['capitulo']}:{v['versiculo']}"
					linhas.append(f"{v['texto']} - {ref_line}")
			if not linhas:
				if ui:
					ui.message("Nada para copiar.")
				return
			textoCopiar = "\n".join(linhas)
			copiedCount = len(linhas)
		elif self.nivel == "favoritos":
			indices = list(self._markedIndices)
			if not indices:
				sel = self.lista.GetSelection()
				if sel != wx.NOT_FOUND:
					indices = [sel]
			inicio = self.favPaginaAtual * self.favItensPorPagina
			linhas = []
			for i in indices:
				realIdx = inicio + i
				if 0 <= realIdx < len(self.favoritos):
					f = self.favoritos[realIdx]
					livroNome = NOMES_LIVROS.get(f["livro"], f["livro"])
					linhas.append(f"{f['texto']} - {livroNome} {f['capitulo']}:{f['versiculo']}")
			if not linhas:
				if ui:
					ui.message("Nada para copiar.")
				return
			textoCopiar = "\n".join(linhas)
			copiedCount = len(linhas)
		elif self.nivel == "capitulos":
			indices = list(self._markedIndices)
			if not indices:
				sel = self.lista.GetSelection()
				if sel != wx.NOT_FOUND:
					indices = [sel]
			linhas = []
			livroNome = NOMES_LIVROS.get(self.livroAtual, self.livroAtual or "")
			for i in indices:
				try:
					capStr = self._strip_prefix(self.lista.GetString(i)).strip()
					linhas.append(f"{livroNome} {capStr}")
				except Exception:
					pass
			if not linhas:
				if ui:
					ui.message("Nada para copiar.")
				return
			textoCopiar = "\n".join(linhas)
			copiedCount = len(linhas)
		else:
			if ui:
				ui.message("Copiar não disponível no índice de livros.")
			return

		def _done_msg():
			try:
				if self.nivel == "versiculos" and ref:
					ui.message(f"Copiado: {ref}")
				else:
					ui.message(f"Copiado {copiedCount} item(s).")
			except Exception:
				pass

		self._copyTextAsync(textoCopiar, onDone=_done_msg)

	def adicionarNota(self):
		if self.nivel != "versiculos":
			if ui:
				ui.message("Abra um capítulo para adicionar notas")
			return

		dlg = wx.Dialog(self, title="Adicionar Nota" + (f" – {self.versaoAtual}" if self.versaoAtual else ""))
		vbox = wx.BoxSizer(wx.VERTICAL)

		lblTexto = wx.StaticText(dlg, label="Digite sua anotação:")
		txtNota = wx.TextCtrl(dlg, style=wx.TE_MULTILINE, name="Texto da anotação")
		vbox.Add(lblTexto, 0, wx.ALL, 5)
		vbox.Add(txtNota, 1, wx.EXPAND | wx.ALL, 5)

		chkVersiculo = wx.CheckBox(dlg, label="Associar ao versículo selecionado")
		vbox.Add(chkVersiculo, 0, wx.ALL, 5)

		hbox = wx.BoxSizer(wx.HORIZONTAL)
		btnOK = wx.Button(dlg, wx.ID_OK, "Salvar")
		btnCancel = wx.Button(dlg, wx.ID_CANCEL, "Cancelar")
		hbox.Add(btnOK, 0, wx.ALL, 5)
		hbox.Add(btnCancel, 0, wx.ALL, 5)
		vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

		dlg.SetSizerAndFit(vbox)
		self._bind_global_shortcuts_to_dialog(dlg)

		if dlg.ShowModal() == wx.ID_OK:
			notaTxt = txtNota.GetValue().strip()
			if notaTxt:
				novaNota = {
					"livro": self.livroAtual,
					"capitulo": self.capituloAtual,
					"nota": notaTxt
				}
				if chkVersiculo.GetValue():
					idx = self.lista.GetSelection()
					if idx != wx.NOT_FOUND and idx < len(self._versosLista):
						novaNota["versiculo"] = self._versosLista[idx]["versiculo"]

				self.notesManager.add(novaNota)
				self.notas.append(novaNota)
				self.indexNotasPorLivro[self.livroAtual].append(novaNota)
				try:
					if not self._temHeaderNotas:
						self.lista.Append("---- Anotações ----")
						self._temHeaderNotas = True
					self.lista.Append(
						f"Nota {novaNota.get('versiculo', 'capítulo ' + str(self.capituloAtual))}: {novaNota['nota']}"
					)
					self._notasLista.append(novaNota)
					self._renderLeituraCapitulo(self.livroAtual, self.capituloAtual,
						[self._formatVersoLine(v, any(s is v for s in self._versosSelecionados)) for v in self._versosLista],
						self._notasLista)
				except Exception:
					self.mostrarVersiculos(self.livroAtual, self.capituloAtual)
		dlg.Destroy()

	def removerNota(self):
		if self.nivel != "versiculos":
			if ui:
				ui.message("Abra um capítulo para remover notas")
			return

		idx = self.lista.GetSelection()
		if idx == wx.NOT_FOUND:
			return

		numVersos = len(self._versosLista)
		notaIndexBase = numVersos + (1 if self._temHeaderNotas else 0)
		notaIdx = idx - notaIndexBase

		if notaIdx < 0 or notaIdx >= len(self._notasLista):
			if ui:
				ui.message("Selecione uma nota para remover")
			return

		nota = self._notasLista[notaIdx]

		dlg = wx.MessageDialog(self,
			f"Remover esta nota?\n\n{nota['nota']}",
			"Confirmar remoção",
			wx.YES_NO | wx.ICON_WARNING)
		self._bind_global_shortcuts_to_dialog(dlg)
		if dlg.ShowModal() == wx.ID_YES:
			try:
				self.notas.remove(nota)
				try:
					self.indexNotasPorLivro[self.livroAtual].remove(nota)
				except Exception:
					pass
				self.notesManager.remove(nota)
				try:
					self.lista.Delete(idx)
					try:
						self._notasLista.remove(nota)
					except Exception:
						pass
					if not self._notasLista and self._temHeaderNotas:
						self.lista.Delete(numVersos)
						self._temHeaderNotas = False
					if ui:
						ui.message("Nota removida com sucesso")
					self._renderLeituraCapitulo(self.livroAtual, self.capituloAtual,
						[self._formatVersoLine(v, any(s is v for s in self._versosSelecionados)) for v in self._versosLista],
						self._notasLista)
				except Exception:
					self.mostrarVersiculos(self.livroAtual, self.capituloAtual)
			except Exception as e:
				if ui:
					ui.message(f"Erro ao remover nota: {e}")
		dlg.Destroy()

	def buscar(self):
		self._pararLeituraSeAtiva()
		dlg = wx.Dialog(self, title="Pesquisar na Bíblia" + (f" – {self.versaoAtual}" if self.versaoAtual else ""))
		vbox = wx.BoxSizer(wx.VERTICAL)

		try:
			lblTermo = wx.StaticText(dlg, label="Termo de busca:")
			txtTermo = wx.TextCtrl(dlg, name="Termo de busca")
			vbox.Add(lblTermo, 0, wx.ALL, 5)
			vbox.Add(txtTermo, 0, wx.EXPAND | wx.ALL, 5)

			chkPalavraInteira = wx.CheckBox(dlg, label="Coincidir palavra inteira")
			chkSemAcento = wx.CheckBox(dlg, label="Ignorar acentos (recomendado)")
			chkSemAcento.SetValue(True)
			vbox.Add(chkPalavraInteira, 0, wx.ALL, 5)
			vbox.Add(chkSemAcento, 0, wx.ALL, 5)

			lblLivro = wx.StaticText(dlg, label="Filtrar por livro (opcional):")
			displayByKey = {}
			for key in self.bibleManager.bible_tree.keys():
				displayByKey[key] = NOMES_LIVROS.get(key, key)
			keyByDisplay = {display: key for key, display in displayByKey.items()}

			choices = ["(Todos)"] + list(keyByDisplay.keys())
			cmbLivro = wx.ComboBox(dlg, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY, name="Filtrar por livro")
			cmbLivro.SetSelection(0)
			vbox.Add(lblLivro, 0, wx.ALL, 5)
			vbox.Add(cmbLivro, 0, wx.EXPAND | wx.ALL, 5)

			hbox = wx.BoxSizer(wx.HORIZONTAL)
			btnOK = wx.Button(dlg, wx.ID_OK, "Pesquisar")
			btnCancel = wx.Button(dlg, wx.ID_CANCEL, "Cancelar")
			hbox.Add(btnOK, 0, wx.ALL, 5)
			hbox.Add(btnCancel, 0, wx.ALL, 5)
			vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

			dlg.SetSizerAndFit(vbox)
			dlg.CenterOnParent()
			self._bind_global_shortcuts_to_dialog(dlg)

			res = dlg.ShowModal()

			termo = txtTermo.GetValue().strip()
			palavraInteira = chkPalavraInteira.GetValue()
			ignorarAcento = chkSemAcento.GetValue()
			livroSelecionado = cmbLivro.GetStringSelection()

			dlg.Destroy()

			wx.SafeYield()

			if res == wx.ID_OK:
				filtroLivroKey = None
				if livroSelecionado != "(Todos)":
					filtroLivroKey = keyByDisplay.get(livroSelecionado)

				if termo:
					self._ultimoTermoBusca = termo
					self._ultimoFiltroLivro = filtroLivroKey
					if ignorarAcento:
						termoBase = normalizar(termo)
						def textoProcessado(t): return normalizar(t)
					else:
						termoBase = termo
						def textoProcessado(t): return t
					if palavraInteira:
						padrao = re.compile(rf"\b{re.escape(termoBase)}\b", re.IGNORECASE)
					else:
						padrao = re.compile(re.escape(termoBase), re.IGNORECASE)

					if filtroLivroKey:
						iterator_fonte = (
							v for caps in self.bibleManager.bible_tree.get(filtroLivroKey, {}).values()
							for v in caps
						)
					else:
						iterator_fonte = (
							v for lista_versos in self.bibleManager.indexPorLivro.values()
							for v in lista_versos
						)

					resultados = []
					try:
						count_check = 0
						for v in iterator_fonte:
							if count_check % 3000 == 0:
								wx.SafeYield()
							count_check += 1
							if padrao.search(textoProcessado(v["texto"])):
								resultados.append(v)
					except Exception:
						if ui:
							ui.message("Erro durante a pesquisa.")
						return

					self._push_navigation_state()
					self.resultadosBusca = resultados
					self.paginaAtual = 0
					self.mostrarResultadosBusca()

		except Exception:
			try:
				dlg.Destroy()
			except Exception:
				pass
			if ui:
				ui.message("Não é possível pesquisar nesta versão.")

	def irParaNumero(self):
		if self.nivel not in ("capitulos", "versiculos"):
			self.anunciar("Disponível apenas na lista de capítulos ou versículos.")
			return

		if self.nivel == "capitulos":
			caps = self.capitulos
			nomeLivro = NOMES_LIVROS.get(self.livroAtual, self.livroAtual)
			prompt = f"{nomeLivro} — Digite o número do capítulo (1–{caps[-1]}):"
		else:
			numVersos = len(self._versosLista)
			nomeLivro = NOMES_LIVROS.get(self.livroAtual, self.livroAtual)
			prompt = f"{nomeLivro} {self.capituloAtual} — Digite o número do versículo (1–{numVersos}):"

		dlg = wx.TextEntryDialog(self, prompt, "Ir para número")
		self._bind_global_shortcuts_to_dialog(dlg)
		if dlg.ShowModal() == wx.ID_OK:
			texto = dlg.GetValue().strip()
			dlg.Destroy()
			if not texto.isdigit():
				self.anunciar("Entrada inválida. Digite apenas números.")
				return
			num = int(texto)
			if self.nivel == "capitulos":
				if num in caps:
					idx = caps.index(num)
					self.lista.SetSelection(idx)
					self.lista.EnsureVisible(idx)
					self.lista.SetFocus()
				else:
					wx.MessageBox(
						f"O capítulo {num} não existe em {nomeLivro}.\nEscolha um capítulo entre 1 e {caps[-1]}.",
						"Capítulo não encontrado",
						wx.OK | wx.ICON_WARNING
					)
			else:
				versos = [v["versiculo"] for v in self._versosLista]
				if num in versos:
					idx = versos.index(num)
					self.lista.SetSelection(idx)
					self.lista.EnsureVisible(idx)
					self.lista.SetFocus()
					v_obj = self._versosLista[idx]
					self.anunciar(f"{v_obj['versiculo']}: {v_obj['texto']}")
				else:
					wx.MessageBox(
						f"O versículo {num} não existe em {nomeLivro} {self.capituloAtual}.\nEscolha um versículo entre 1 e {numVersos}.",
						"Versículo não encontrado",
						wx.OK | wx.ICON_WARNING
					)
		else:
			dlg.Destroy()

	def irParaReferencia(self):
		self._pararLeituraSeAtiva()
		while True:
			dlg = wx.TextEntryDialog(self, "Digite a referência (Ex: Jo 3:16, Gn 1 1, 3Jo 1):", "Ir para referência")
			self._bind_global_shortcuts_to_dialog(dlg)
			if dlg.ShowModal() == wx.ID_OK:
				texto = dlg.GetValue().strip()
				dlg.Destroy()
				if not texto:
					continue

				match = re.match(r"^(\d?\s*[a-zA-Z\u00C0-\u00FF]+)[\s\.]*(\\d+)[:\.\s]*(\d*)$", texto)
				if match:
					livro_str = match.group(1).strip()
					cap_str = match.group(2)
					vers_str = match.group(3)

					livro_key = None

					for sigla in NOMES_LIVROS:
						if sigla.lower() == livro_str.lower():
							livro_key = sigla
							break

					if not livro_key:
						busca = normalizar(livro_str)
						for sigla in NOMES_LIVROS:
							if normalizar(sigla) == busca:
								livro_key = sigla
								break

					if not livro_key:
						busca = normalizar(livro_str)
						for sigla, nome in NOMES_LIVROS.items():
							if normalizar(nome).startswith(busca):
								livro_key = sigla
								break

					if not livro_key:
						wx.MessageBox("Livro não encontrado.", "Erro", wx.OK | wx.ICON_ERROR)
						continue

					try:
						cap = int(cap_str)
						caps_livro = self.bibleManager.bible_tree.get(livro_key)

						if not caps_livro:
							wx.MessageBox(f"O livro de {NOMES_LIVROS.get(livro_key, livro_key)} não está disponível nesta versão da Bíblia.", "Indisponível", wx.OK | wx.ICON_WARNING)
							continue

						if cap not in caps_livro:
							wx.MessageBox(f"Capítulo {cap} não encontrado em {NOMES_LIVROS.get(livro_key, livro_key)}.", "Erro", wx.OK | wx.ICON_ERROR)
							continue

						self._push_navigation_state()
						self.mostrarVersiculos(livro_key, cap)

						if vers_str:
							vers = int(vers_str)
							versos_cap = self.bibleManager.bible_tree[livro_key][cap]
							try:
								pos = [v["versiculo"] for v in versos_cap].index(vers)
								self.lista.SetSelection(pos)
								self.lista.EnsureVisible(pos)
								self.lista.SetFocus()
								v_obj = versos_cap[pos]
								texto_anuncio = f"{v_obj['versiculo']}: {v_obj['texto']}"
								self.anunciar(texto_anuncio)
							except ValueError:
								wx.MessageBox(f"Versículo {vers} não encontrado.", "Erro", wx.OK | wx.ICON_ERROR)
						break
					except Exception:
						wx.MessageBox("Referência inválida.", "Erro", wx.OK | wx.ICON_ERROR)
						continue
				else:
					wx.MessageBox("Formato inválido. Use Ex: Jo 3:16", "Erro", wx.OK | wx.ICON_ERROR)
					continue
			else:
				dlg.Destroy()
				break

	def mostrarResultadosBusca(self):
		self._pararLeituraSeAtiva()
		self.nivel = "busca"
		self._trocarLista(usarListBox=True)
		self._resetMarksForLevel()
		self.lista.Freeze()
		self.lista.Clear()
		inicio = self.paginaAtual * self.itensPorPagina
		fim = inicio + self.itensPorPagina
		pagina = self.resultadosBusca[inicio:fim]
		linhas = [
			f"{v['texto']} - {NOMES_LIVROS.get(v['livro'], v['livro'])} {v['capitulo']}:{v['versiculo']}"
			for v in pagina
		]
		if linhas:
			self.lista.AppendItems(linhas)
		self.lista.Thaw()

		if linhas:
			self.lista.SetSelection(0)
		else:
			self.lista.SetSelection(wx.NOT_FOUND)

		total = len(self.resultadosBusca)
		totalPaginas = (total - 1) // self.itensPorPagina if total > 0 else 0

		self.SetTitle("Open Bible" + (f" – {self.versaoAtual}" if self.versaoAtual else "") + f" – Resultados da busca (página {self.paginaAtual+1} de {totalPaginas+1})")

		if ui:
			msg = f"Foram encontrados {total} versículos. Página {self.paginaAtual+1} de {totalPaginas+1}."
			ui.message(msg)

		self._updateButtonsForSearch()

		wx.CallAfter(self._ensureListFocus)

		try:
			self._atualizarContexto(livro=None, capitulo=None)
			self.txtLeitura.Freeze()
			self.txtLeitura.SetValue("\n".join(linhas))
			self.txtLeitura.ShowPosition(0)
			self.txtLeitura.Thaw()
		except Exception:
			pass
		self.leituraIndice = 0
		self._leituraTotalVersos = 0

	def paginaAnterior(self):
		if self.nivel == "busca" and self.paginaAtual > 0:
			self.paginaAtual -= 1
			self.mostrarResultadosBusca()

	def paginaProxima(self):
		if self.nivel == "busca":
			totalPaginas = (len(self.resultadosBusca) - 1) // self.itensPorPagina if self.resultadosBusca else 0
			if self.paginaAtual < totalPaginas:
				self.paginaAtual += 1
				self.mostrarResultadosBusca()

	def limparBusca(self):
		self.resultadosBusca = []
		self.paginaAtual = 0
		self.btnLimparBusca.Disable()
		if not self._restore_navigation_state():
			self.mostrarLivros()

	def _formatFavoritoLinha(self, fav):
		livroNome = NOMES_LIVROS.get(fav["livro"], fav["livro"])
		return f"{fav['texto']} - {livroNome} {fav['capitulo']}:{fav['versiculo']}"

	def adicionarFavoritoAtual(self):
		items = []

		if self.nivel == "versiculos":
			if self._versosSelecionados:
				for v in sorted(self._versosSelecionados, key=lambda x: x["versiculo"]):
					items.append({
						"livro": self.livroAtual,
						"capitulo": self.capituloAtual,
						"versiculo": v["versiculo"],
						"texto": v["texto"]
					})
			else:
				idx = self.lista.GetSelection()
				numVersos = len(self._versosLista)
				if idx == wx.NOT_FOUND or idx >= numVersos:
					if ui:
						ui.message("Selecione um versículo para favoritar")
					return
				v = self._versosLista[idx]
				items.append({
					"livro": self.livroAtual,
					"capitulo": self.capituloAtual,
					"versiculo": v["versiculo"],
					"texto": v["texto"]
				})
		elif self.nivel == "busca":
			idx = self.lista.GetSelection()
			if idx == wx.NOT_FOUND:
				if ui:
					ui.message("Selecione um resultado para favoritar")
				return
			inicio = self.paginaAtual * self.itensPorPagina
			realIdx = inicio + idx
			if 0 <= realIdx < len(self.resultadosBusca):
				v = self.resultadosBusca[realIdx]
				items.append({
					"livro": v["livro"],
					"capitulo": v["capitulo"],
					"versiculo": v["versiculo"],
					"texto": v["texto"]
				})
			else:
				if ui:
					ui.message("Seleção inválida para favoritar")
				return
		else:
			if ui:
				ui.message("Ctrl+F funciona em capítulos (versículos) e nos resultados da busca")
			return

		self.favoritesManager.add_many(items)
		self.favoritos = self.favoritesManager.all()
		if ui:
			if len(items) == 1:
				fav = items[0]
				livroNome = NOMES_LIVROS.get(fav["livro"], fav["livro"])
				ui.message(f"Favorito adicionado: {livroNome} {fav['capitulo']}:{fav['versiculo']}")
			else:
				livroNome = NOMES_LIVROS.get(self.livroAtual or items[0]["livro"], self.livroAtual or items[0]["livro"])
				ui.message(f"{len(items)} favoritos adicionados em {livroNome}")

	def removerFavoritoAtual(self):
		if self.nivel != "favoritos":
			return
		idx = self.lista.GetSelection()
		if idx == wx.NOT_FOUND:
			return
		inicio = self.favPaginaAtual * self.favItensPorPagina
		realIdx = inicio + idx
		if 0 <= realIdx < len(self.favoritos):
			fav = self.favoritos[realIdx]
			if wx.MessageBox(f"Remover favorito?\n\n{self._formatFavoritoLinha(fav)}", "Confirmar remoção", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
				self.favoritesManager.remove_at_index(realIdx)
				self.favoritos = self.favoritesManager.all()
				totalPaginas = (len(self.favoritos) - 1) // self.favItensPorPagina if self.favoritos else 0
				if self.favPaginaAtual > totalPaginas:
					self.favPaginaAtual = max(0, totalPaginas)
				self.mostrarFavoritos()
				if ui:
					ui.message("Favorito removido")

	def mostrarFavoritos(self):
		self._pararLeituraSeAtiva()
		self.nivel = "favoritos"
		self._trocarLista(usarListBox=True)
		self._resetMarksForLevel()
		self.lista.Freeze()
		self.lista.Clear()
		inicio = self.favPaginaAtual * self.favItensPorPagina
		fim = inicio + self.favItensPorPagina
		pagina = self.favoritos[inicio:fim]
		linhas = [self._formatFavoritoLinha(f) for f in pagina]
		if linhas:
			self.lista.AppendItems(linhas)
		self.lista.Thaw()
		if linhas:
			self.lista.SetSelection(0)
		else:
			self.lista.SetSelection(wx.NOT_FOUND)
		total = len(self.favoritos)
		totalPaginas = (total - 1) // self.favItensPorPagina if total > 0 else 0
		self.SetTitle("Open Bible" + (f" – {self.versaoAtual}" if self.versaoAtual else "") + f" – Favoritos (página {self.favPaginaAtual+1} de {totalPaginas+1})")
		if ui:
			ui.message(f"{total} favoritos. Página {self.favPaginaAtual+1} de {totalPaginas+1}.")
		self._updateButtonsForFavorites()
		wx.CallAfter(self._ensureListFocus)
		try:
			self._atualizarContexto(livro=None, capitulo=None)
			self.txtLeitura.Freeze()
			self.txtLeitura.SetValue("\n".join(linhas))
			self.txtLeitura.ShowPosition(0)
			self.txtLeitura.Thaw()
		except Exception:
			pass
		self.leituraIndice = 0
		self._leituraTotalVersos = 0

	def paginaFavoritosAnterior(self):
		if self.nivel == "favoritos" and self.favPaginaAtual > 0:
			self.favPaginaAtual -= 1
			self.mostrarFavoritos()

	def paginaFavoritosProxima(self):
		if self.nivel == "favoritos":
			totalPaginas = (len(self.favoritos) - 1) // self.favItensPorPagina if self.favoritos else 0
			if self.favPaginaAtual < totalPaginas:
				self.favPaginaAtual += 1
				self.mostrarFavoritos()

	def mostrarCapitulosLidos(self):
		self._pararLeituraSeAtiva()
		self.nivel = "lidos"
		self._trocarLista(usarListBox=True)
		self._resetMarksForLevel()

		self.lidosLista = self.readManager.all()
		ordem_livros = list(NOMES_LIVROS.keys())
		def sort_key(x):
			try:
				idx = ordem_livros.index(x["livro"])
			except ValueError:
				idx = 999
			return idx, x["capitulo"]
		self.lidosLista.sort(key=sort_key)

		self.lista.Freeze()
		self.lista.Clear()

		inicio = self.lidosPaginaAtual * self.lidosItensPorPagina
		fim = inicio + self.lidosItensPorPagina
		pagina = self.lidosLista[inicio:fim]

		linhas = [f"{NOMES_LIVROS.get(l['livro'], l['livro'])} - Capítulo {l['capitulo']}" for l in pagina]

		if linhas:
			self.lista.AppendItems(linhas)
		self.lista.Thaw()

		if linhas:
			self.lista.SetSelection(0)
		else:
			self.lista.SetSelection(wx.NOT_FOUND)

		total = len(self.lidosLista)
		totalPaginas = (total - 1) // self.lidosItensPorPagina if total > 0 else 0

		self.SetTitle("Open Bible" + (f" – {self.versaoAtual}" if self.versaoAtual else "") + f" – Capítulos Lidos (página {self.lidosPaginaAtual+1} de {totalPaginas+1})")
		if ui:
			ui.message(f"{total} capítulos lidos. Página {self.lidosPaginaAtual+1} de {totalPaginas+1}.")

		self._updateButtonsForLidos()
		wx.CallAfter(self._ensureListFocus)

		try:
			self._atualizarContexto(livro=None, capitulo=None)
			self.txtLeitura.Freeze()
			self.txtLeitura.SetValue("\n".join(linhas))
			self.txtLeitura.ShowPosition(0)
			self.txtLeitura.Thaw()
		except Exception:
			pass
		self.leituraIndice = 0
		self._leituraTotalVersos = 0

	def _navToLidos(self):
		self._push_navigation_state()
		self.mostrarCapitulosLidos()

	def _navToFavoritos(self):
		self._push_navigation_state()
		self.mostrarFavoritos()

	def paginaLidosAnterior(self):
		if self.nivel == "lidos" and self.lidosPaginaAtual > 0:
			self.lidosPaginaAtual -= 1
			self.mostrarCapitulosLidos()

	def paginaLidosProxima(self):
		if self.nivel == "lidos":
			totalPaginas = (len(self.lidosLista) - 1) // self.lidosItensPorPagina if self.lidosLista else 0
			if self.lidosPaginaAtual < totalPaginas:
				self.lidosPaginaAtual += 1
				self.mostrarCapitulosLidos()

	def onKeyDown(self, event):
		keyCode = event.GetKeyCode()
		ctrl = event.ControlDown()
		shift = event.ShiftDown()
		alt = event.AltDown()
		no_modifiers = not ctrl and not shift and not alt

		if self.nivel == "busca":
			if keyCode == wx.WXK_PAGEUP and no_modifiers:
				self.paginaAnterior()
				return
			if keyCode == wx.WXK_PAGEDOWN and no_modifiers:
				self.paginaProxima()
				return
		if self.nivel == "favoritos":
			if keyCode == wx.WXK_PAGEUP and no_modifiers:
				self.paginaFavoritosAnterior()
				return
			if keyCode == wx.WXK_PAGEDOWN and no_modifiers:
				self.paginaFavoritosProxima()
				return
			if keyCode == wx.WXK_DELETE and no_modifiers:
				self.removerFavoritoAtual()
				return
		if self.nivel == "lidos":
			if keyCode == wx.WXK_PAGEUP and no_modifiers:
				self.paginaLidosAnterior()
				return
			if keyCode == wx.WXK_PAGEDOWN and no_modifiers:
				self.paginaLidosProxima()
				return

		event.Skip()

	def onChar(self, event):
		keyCode = event.GetKeyCode()
		ctrl = event.ControlDown()
		shift = event.ShiftDown()
		alt = event.AltDown()

		focused_obj = wx.Window.FindFocus()
		is_interactive = isinstance(focused_obj, (wx.Button, wx.TextCtrl, wx.CheckBox, wx.ComboBox, wx.SearchCtrl))

		if keyCode == wx.WXK_ESCAPE:
			self.voltar()
			return
		if keyCode == wx.WXK_F1:
			self.mostrarAjudaRapida()
			return
		if keyCode == wx.WXK_F5:
			self.irParaNumero()
			return

		if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			if is_interactive:
				event.Skip()
				return
			self.abrir()
			return

		if keyCode == wx.WXK_SPACE:
			if is_interactive:
				event.Skip()
				return
			self._toggleMarkCurrentItem()
			return

		if ctrl and not shift and not alt and keyCode == ord('A'):
			self._markAllCurrent()
			return
		if ctrl and not shift and not alt and keyCode == ord('Z'):
			self._clearMarks_global()
			return
		if ctrl and not shift and not alt and keyCode == ord('E'):
			self.abrirEditorTexto()
			return
		if ctrl and shift and not alt and keyCode == ord('C'):
			self._push_navigation_state()
			self._compararVersiculoSelecionado()
			return
		if ctrl and not shift and not alt and keyCode == ord('C'):
			self._copyMarkedOrSelected()
			return
		if ctrl and not shift and not alt and keyCode == ord('I'):
			self.mostrarLivros()
			return
		if ctrl and not shift and not alt and keyCode == ord('L'):
			self._toggleLeitura()
			return

		if keyCode == wx.WXK_LEFT and not alt and not ctrl and not shift and self.nivel == "versiculos":
			if self.capitulos and self.capituloAtual == self.capitulos[0]:
				wx.CallAfter(self.livroAnterior)
			else:
				wx.CallAfter(self.capituloAnterior)
			return
		if keyCode == wx.WXK_RIGHT and not alt and not ctrl and not shift and self.nivel == "versiculos":
			if self.capitulos and self.capituloAtual == self.capitulos[-1]:
				wx.CallAfter(self.proximoLivro)
			else:
				wx.CallAfter(self.proximoCapitulo)
			return

		if ctrl and not shift and not alt and keyCode == ord('N'):
			self.adicionarNota()
			return
		if ctrl and not shift and not alt and keyCode == wx.WXK_DELETE:
			self.removerNota()
			return
		if ctrl and not shift and not alt and keyCode == ord('P'):
			self.buscar()
			return
		if ctrl and not shift and not alt and keyCode == ord('R'):
			self.irParaReferencia()
			return
		if ctrl and shift and not alt and keyCode == ord('F'):
			self._navToFavoritos()
			return
		if ctrl and not shift and not alt and keyCode == ord('F'):
			self.adicionarFavoritoAtual()
			return
		if ctrl and not shift and not alt and keyCode == ord('G'):
			self.abrirGerenciadorBiblias()
			return
		if ctrl and not shift and not alt and keyCode == ord('B'):
			self.abrirDialogoBackup(None)
			return
		if ctrl and not shift and not alt and keyCode == ord('M'):
			self.toggleMarcarCapituloLido()
			return
		if ctrl and shift and not alt and keyCode == ord('M'):
			self._navToLidos()
			return
		if ctrl and not shift and not alt and keyCode == ord('T'):
			self._alternarVersaoCiclico()
			return
		if ctrl and not alt and (keyCode == wx.WXK_ADD or keyCode == ord('+') or keyCode == wx.WXK_NUMPAD_ADD):
			self._ajustarFonte(1)
			return
		if ctrl and not alt and (keyCode == wx.WXK_SUBTRACT or keyCode == ord('-') or keyCode == wx.WXK_NUMPAD_SUBTRACT):
			self._ajustarFonte(-1)
			return
		event.Skip()

	def _alternarVersaoCiclico(self):
		try:
			nomes = self.bibleManager.listar_nomes()
			if not nomes:
				self.anunciar("Nenhuma versão disponível.")
				return
			if self.versaoAtual not in nomes:
				nova = nomes[0]
			else:
				idx = nomes.index(self.versaoAtual)
				nova = nomes[(idx + 1) % len(nomes)]

			biblia = self.bibleManager.carregar(nova)
			nm = NotesManager(nova)
			self.biblia = biblia
			self.notas = nm.all()
			self.notesManager = nm
			self.versaoAtual = nova
			self._buildNotesIndex()

			if self.livroAtual and self.capituloAtual:
				self.mostrarVersiculos(self.livroAtual, self.capituloAtual)
				self.anunciar(
					f"Versão alterada para {nova}, mantendo "
					f"{NOMES_LIVROS.get(self.livroAtual, self.livroAtual)} capítulo {self.capituloAtual}"
				)
			else:
				self.mostrarLivros()
				self.anunciar(f"Versão alterada para {nova}")
		except Exception as e:
			self.anunciar(f"Erro ao alternar versão: {e}")

	def _onListSelectionChanged(self, event):
		if self.nivel == "versiculos":
			idx = self.lista.GetSelection()
			numVersos = len(self._versosLista)
			isNotaSelecionada = False
			if idx != wx.NOT_FOUND:
				if self._temHeaderNotas and idx >= (numVersos + 1):
					notaIndexBase = numVersos + 1
					notaIdx = idx - notaIndexBase
					isNotaSelecionada = 0 <= notaIdx < len(self._notasLista)
				elif not self._temHeaderNotas and idx >= numVersos:
					isNotaSelecionada = False
			if isNotaSelecionada and self._notasLista:
				try:
					self.btnRemoverNota.Enable()
				except Exception:
					pass
			else:
				try:
					self.btnRemoverNota.Disable()
				except Exception:
					pass

			if idx != wx.NOT_FOUND and idx < numVersos:
				v = self._versosLista[idx]
				try:
					self._atualizarContexto()
					novoTexto = f"{v['versiculo']}: {v['texto']}"
					self._pendingTxtVerso = novoTexto
					if self._txtUpdateTimer.IsRunning():
						self._txtUpdateTimer.Stop()
					self._txtUpdateTimer.Start(80, oneShot=True)
					if not self.leituraAtiva:
						self.leituraIndice = idx
				except Exception:
					pass

		elif self.nivel in ("busca", "favoritos", "lidos"):
			idx = self.lista.GetSelection()
			if idx != wx.NOT_FOUND:
				try:
					novoTexto = self._strip_prefix(self.lista.GetString(idx))
					self._pendingTxtVerso = novoTexto
					if self._txtUpdateTimer.IsRunning():
						self._txtUpdateTimer.Stop()
					self._txtUpdateTimer.Start(80, oneShot=True)
				except Exception:
					pass
		event.Skip()

	def _compararVersiculoSelecionado(self):
		self._pararLeituraSeAtiva()
		if self.nivel != "versiculos":
			if ui:
				ui.message("Abra um capítulo e selecione um versículo para comparar.")
			return
		idx = self.lista.GetSelection()
		numVersos = len(self._versosLista)
		if idx == wx.NOT_FOUND or idx >= numVersos:
			if ui:
				ui.message("Selecione um versículo para comparar.")
			return
		verso = self._versosLista[idx]
		livro = self.livroAtual
		cap = self.capituloAtual
		vers = verso["versiculo"]

		dlg = wx.Dialog(self, title="Comparar versículo entre versões", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		vbox = wx.BoxSizer(wx.VERTICAL)

		info = wx.StaticText(dlg, label=f"Selecione até 10 versões para comparar {NOMES_LIVROS.get(livro, livro)} {cap}:{vers}")
		vbox.Add(info, 0, wx.ALL, 8)

		todas = self.bibleManager.listar_nomes()
		if self.versaoAtual in todas:
			todas = [self.versaoAtual] + [n for n in todas if n != self.versaoAtual]
		clb = wx.CheckListBox(dlg, choices=todas, style=wx.LB_SINGLE, name="Lista de versões")

		vbox.Add(clb, 1, wx.EXPAND | wx.ALL, 8)

		if todas:
			clb.Check(0, True)

		aviso = wx.StaticText(dlg, label="Limite: 10.")
		vbox.Add(aviso, 0, wx.ALL, 6)

		hbox = wx.BoxSizer(wx.HORIZONTAL)
		btnOK = wx.Button(dlg, wx.ID_OK, "Comparar")
		btnCancel = wx.Button(dlg, wx.ID_CANCEL, "Cancelar")
		hbox.Add(btnOK, 0, wx.ALL, 5)
		hbox.Add(btnCancel, 0, wx.ALL, 5)
		vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

		dlg.SetSizerAndFit(vbox)
		dlg.CenterOnParent()
		self._bind_global_shortcuts_to_dialog(dlg)

		def onCheck(evt):
			idxEvt = evt.GetInt()
			marcados = [i for i in range(clb.GetCount()) if clb.IsChecked(i)]
			if len(marcados) > 10:
				clb.Check(idxEvt, False)
				if ui:
					ui.message("Limite de seleção atingido.")
				evt.Skip()
				return

			try:
				estado = "Marcada" if clb.IsChecked(idxEvt) else "Desmarcada"
				if ui:
					ui.message(estado)
			except Exception:
				pass
			evt.Skip()
		clb.Bind(wx.EVT_CHECKLISTBOX, onCheck)

		def onSelectionChanged(evt):
			try:
				sel = clb.GetSelection()
				if sel != wx.NOT_FOUND:
					estado = "Marcada" if clb.IsChecked(sel) else "Desmarcada"
					wx.CallLater(100, lambda: self.anunciar(estado))
			except Exception:
				pass
			evt.Skip()
		try:
			clb.Bind(wx.EVT_LISTBOX, onSelectionChanged)
		except Exception:
			pass

		def _clbCharHook(e):
			if e.GetKeyCode() == wx.WXK_F1:
				try:
					self.mostrarAjudaRapida()
				except Exception:
					pass
				return
			e.Skip()
		try:
			clb.Bind(wx.EVT_CHAR_HOOK, _clbCharHook)
		except Exception:
			pass

		if dlg.ShowModal() == wx.ID_OK:
			selecionadas = [todas[i] for i in range(clb.GetCount()) if clb.IsChecked(i)]
			if not selecionadas:
				selecionadas = [self.versaoAtual]
			compEntries = []

			def safe_compare(a, b):
				return str(a).strip().lower() == str(b).strip().lower()

			if ui:
				ui.message("Comparando versões, aguarde...")
			for versao in selecionadas:
				try:
					bib_tree = self.bibleManager.bible_tree if versao == self.versaoAtual else None
					texto = None
					if bib_tree is not None:
						versos_cap = bib_tree.get(livro, {}).get(cap, [])
						for v in versos_cap:
							if safe_compare(v.get("versiculo"), vers):
								texto = v.get("texto")
								break
					else:
						bib = self.bibleManager.carregar_para_leitura(versao)
						for v in bib:
							if (safe_compare(v.get("livro"), livro) or
							(v.get("livro", "").strip().lower() == NOMES_LIVROS.get(livro, "").lower())) and safe_compare(v.get("capitulo"), cap) and safe_compare(v.get("versiculo"), vers):
								texto = v.get("texto")
								break
					compEntries.append({"versao": versao, "texto": texto})
				except Exception:
					compEntries.append({"versao": versao, "texto": None})

			def linha_visivel(entry, marcado=False):
				prefix = "✓ " if marcado else ""
				if entry["texto"] is None:
					return f"{prefix}(não encontrado nesta versão) — {entry['versao']}"
				return f"{prefix}{entry['texto']} — {entry['versao']}"

			selecionados_indices = set()
			linhas = [linha_visivel(e, False) for e in compEntries]

			resDlg = wx.Dialog(self, title=f"Comparação — {NOMES_LIVROS.get(livro, livro)} {cap}:{vers}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
			rb = wx.BoxSizer(wx.VERTICAL)
			tip = wx.StaticText(resDlg, label="Dica: Enter abre a versão; Espaço marca/desmarca; Ctrl+A marca todos; Ctrl+Z limpa; Ctrl+C copia os marcados.")
			rb.Add(tip, 0, wx.ALL, 6)
			lb = wx.ListBox(resDlg, choices=linhas, style=wx.LB_SINGLE, name="Versículos comparados")

			rb.Add(lb, 1, wx.EXPAND | wx.ALL, 8)
			btnClose = wx.Button(resDlg, wx.ID_CLOSE, "Fechar")
			rb.Add(btnClose, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
			resDlg.SetSizerAndFit(rb)
			self._bind_global_shortcuts_to_dialog(resDlg)
			btnClose.Bind(wx.EVT_BUTTON, lambda e: resDlg.Close())
			resDlg.CenterOnParent()

			def refresh_lines():
				try:
					lb.Freeze()
				except Exception:
					pass
				try:
					for i in range(lb.GetCount()):
						lb.SetString(i, linha_visivel(compEntries[i], i in selecionados_indices))
				except Exception:
					pass
				finally:
					try:
						lb.Thaw()
					except Exception:
						pass

			def _abrirVersaoEscolhida():
				sel = lb.GetSelection()
				if sel == wx.NOT_FOUND or sel >= len(compEntries):
					return
				versaoEscolhida = compEntries[sel]["versao"]
				try:
					biblia = self.bibleManager.carregar(versaoEscolhida)
					nm = NotesManager(versaoEscolhida)
					self.biblia = biblia
					self.notas = nm.all()
					self.notesManager = nm
					self.versaoAtual = versaoEscolhida
					self._buildNotesIndex()
					self.mostrarVersiculos(livro, cap)
					try:
						pos = [v["versiculo"] for v in self.bibleManager.indexPorLivro[livro] if v["capitulo"] == cap].index(vers)
						self.lista.SetSelection(pos)
						self.lista.SetFocus()
						nomeLivro = NOMES_LIVROS.get(livro, livro)
						self.anunciar(f"Versão atual: {versaoEscolhida}. {nomeLivro} capítulo {cap}")
						textoLinha = self.lista.GetString(pos)
						self.anunciar(textoLinha)
					except Exception:
						nomeLivro = NOMES_LIVROS.get(livro, livro)
						self.anunciar(f"Versão atual: {versaoEscolhida}. {nomeLivro} capítulo {cap}. Versículo {vers} não encontrado nesta versão.")
					resDlg.Close()
				except Exception as e:
					wx.MessageBox(f"Falha ao abrir versão '{versaoEscolhida}': {e}", "Erro", wx.OK | wx.ICON_ERROR)

			lb.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: _abrirVersaoEscolhida())

			def _resCharHook(e):
				nonlocal selecionados_indices
				code = e.GetKeyCode()
				ctrl = e.ControlDown()
				alt = e.AltDown()
				shift = e.ShiftDown()

				focused = wx.Window.FindFocus()
				if isinstance(focused, wx.Button):
					e.Skip()
					return

				if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
					_abrirVersaoEscolhida()
					return

				if code == wx.WXK_SPACE:
					sel = lb.GetSelection()
					if sel != wx.NOT_FOUND:
						if sel in selecionados_indices:
							selecionados_indices.remove(sel)
							if ui:
								ui.message("Item desmarcado")
						else:
							selecionados_indices.add(sel)
							if ui:
								ui.message("Item marcado")
						refresh_lines()
						try:
							lb.SetSelection(sel)
						except Exception:
							pass
					return

				if ctrl and not alt and not shift and code == ord('A'):
					selecionados_indices = set(range(len(compEntries)))
					refresh_lines()
					if ui:
						ui.message("Todos os itens foram marcados")
					return

				if ctrl and not alt and not shift and code == ord('Z'):
					selecionados_indices = set()
					refresh_lines()
					if ui:
						ui.message("Seleção limpa")
					return

				if ctrl and not alt and not shift and code == ord('C'):
					indices_para_copiar = list(selecionados_indices)
					if not indices_para_copiar:
						sel = lb.GetSelection()
						if sel != wx.NOT_FOUND:
							indices_para_copiar = [sel]
					entradas = []
					for i in indices_para_copiar:
						if 0 <= i < len(compEntries):
							ent = compEntries[i]
							if ent["texto"] is not None:
								entradas.append(ent)
					if not entradas:
						if ui:
							ui.message("Nenhum versículo válido para copiar.")
						return
					referencia = f"{NOMES_LIVROS.get(livro, livro)} {cap}:{vers}"
					linhas_copy = [f"{ent['texto']} - {referencia} - {ent['versao']}" for ent in entradas]
					textoCopiar = "\n".join(linhas_copy)
					self._copyTextAsync(textoCopiar, onDone=lambda: ui.message(f"Copiado {len(linhas_copy)} item(s)."))
					return

				if code == wx.WXK_F1:
					try:
						self.mostrarAjudaRapida()
					except Exception:
						pass
					return

				e.Skip()

			try:
				resDlg.Bind(wx.EVT_CHAR_HOOK, _resCharHook)
			except Exception:
				pass

			resDlg.ShowModal()
			resDlg.Destroy()

		dlg.Destroy()

	def _updateButtonsForLevel(self):
		self.btnAnterior.Disable()
		self.btnProximo.Disable()
		self.btnCopiar.Enable()
		self.btnAdicionarNota.Disable()
		self.btnRemoverNota.Disable()
		self.btnPagAnterior.Disable()
		self.btnPagProxima.Disable()
		self.btnLimparBusca.Disable()
		self.btnBuscar.Enable()
		self.btnFavoritos.Enable()

		self._updateVisibleButtons([
			self.btnBuscar, self.btnFavoritos
		])

	def _updateButtonsForChapter(self):
		idx = self.capitulos.index(self.capituloAtual) if (self.capitulos and self.capituloAtual in self.capitulos) else -1
		livrosSiglas = [s for s in NOMES_LIVROS if self.bibleManager.bible_tree.get(s)]
		idxLivro = livrosSiglas.index(self.livroAtual) if self.livroAtual in livrosSiglas else -1
		primeiroCapitulo = (idx == 0)
		ultimoCapitulo = (idx == -1 or idx == len(self.capitulos) - 1)
		temLivroAnterior = (idxLivro > 0)
		temProximoLivro = (idxLivro != -1 and idxLivro < len(livrosSiglas) - 1)

		if idx > 0:
			self.btnAnterior.Enable()
		else:
			self.btnAnterior.Disable()
		if idx != -1 and idx < len(self.capitulos) - 1:
			self.btnProximo.Enable()
		else:
			self.btnProximo.Disable()
		self.btnCopiar.Enable()
		self.btnAdicionarNota.Enable()
		self.btnRemoverNota.Disable()
		self.btnPagAnterior.Disable()
		self.btnPagProxima.Disable()
		self.btnLimparBusca.Disable()
		self.btnBuscar.Enable()
		self.btnFavoritos.Enable()

		botoesVisiveis = [
			self.btnAnterior, self.btnProximo, self.btnMarcarLido,
			self.btnCopiar, self.btnAdicionarNota, self.btnRemoverNota
		]
		if primeiroCapitulo and temLivroAnterior:
			botoesVisiveis.insert(0, self.btnLivroAnterior)
		if ultimoCapitulo and temProximoLivro:
			botoesVisiveis.append(self.btnProximoLivro)
		self._updateVisibleButtons(botoesVisiveis)

	def _updateButtonsForSearch(self):
		self.btnAnterior.Disable()
		self.btnProximo.Disable()
		self.btnCopiar.Enable()
		self.btnAdicionarNota.Disable()
		self.btnRemoverNota.Disable()
		self.btnLimparBusca.Enable()
		totalPaginas = (len(self.resultadosBusca) - 1) // self.itensPorPagina if self.resultadosBusca else 0
		if self.paginaAtual > 0:
			self.btnPagAnterior.Enable()
		else:
			self.btnPagAnterior.Disable()
		if self.paginaAtual < totalPaginas:
			self.btnPagProxima.Enable()
		else:
			self.btnPagProxima.Disable()
		self.btnBuscar.Enable()
		self.btnFavoritos.Enable()

		self._updateVisibleButtons([
			self.btnCopiar, self.btnPagAnterior, self.btnPagProxima, self.btnLimparBusca
		])

	def _updateButtonsForFavorites(self):
		self.btnAnterior.Disable()
		self.btnProximo.Disable()
		self.btnCopiar.Enable()
		self.btnAdicionarNota.Disable()
		self.btnRemoverNota.Disable()
		totalPaginas = (len(self.favoritos) - 1) // self.favItensPorPagina if self.favoritos else 0
		if self.favPaginaAtual > 0:
			self.btnPagAnterior.Enable()
		else:
			self.btnPagAnterior.Disable()
		if self.favPaginaAtual < totalPaginas:
			self.btnPagProxima.Enable()
		else:
			self.btnPagProxima.Disable()
		self.btnLimparBusca.Disable()
		self.btnBuscar.Enable()
		self.btnFavoritos.Enable()

		self._updateVisibleButtons([
			self.btnCopiar, self.btnPagAnterior, self.btnPagProxima
		])

	def _updateButtonsForLidos(self):
		self.btnAnterior.Disable()
		self.btnProximo.Disable()
		self.btnCopiar.Disable()
		self.btnAdicionarNota.Disable()
		self.btnRemoverNota.Disable()
		totalPaginas = (len(self.lidosLista) - 1) // self.lidosItensPorPagina if self.lidosLista else 0
		if self.lidosPaginaAtual > 0:
			self.btnPagAnterior.Enable()
		else:
			self.btnPagAnterior.Disable()
		if self.lidosPaginaAtual < totalPaginas:
			self.btnPagProxima.Enable()
		else:
			self.btnPagProxima.Disable()
		self.btnLimparBusca.Disable()
		self.btnBuscar.Enable()
		self.btnFavoritos.Enable()

		self._updateVisibleButtons([
			self.btnPagAnterior, self.btnPagProxima
		])

	def abrirGerenciadorBiblias(self):
		self._pararLeituraSeAtiva()
		dlg = wx.Dialog(self, title="Gerenciar Bíblias" + (f" – {self.versaoAtual}" if self.versaoAtual else ""), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		vbox = wx.BoxSizer(wx.VERTICAL)

		lbl = wx.StaticText(dlg, label="Versões disponíveis:")
		lst = wx.ListBox(dlg, choices=self.bibleManager.listar_nomes(), style=wx.LB_SINGLE, name="Lista de versões")
		vbox.Add(lbl, 0, wx.ALL, 5)
		vbox.Add(lst, 1, wx.EXPAND | wx.ALL, 5)

		hbox = wx.BoxSizer(wx.HORIZONTAL)
		btnImportar = wx.Button(dlg, label="Importar JSON...")
		btnRemover = wx.Button(dlg, label="Remover versão")
		btnBaixar = wx.Button(dlg, label="Baixar Bíblias")
		btnTornarPadrao = wx.Button(dlg, label="Tornar padrão")
		btnFechar = wx.Button(dlg, wx.ID_CLOSE, "Fechar")
		hbox.Add(btnImportar, 0, wx.ALL, 5)
		hbox.Add(btnRemover, 0, wx.ALL, 5)
		hbox.Add(btnBaixar, 0, wx.ALL, 5)
		hbox.Add(btnTornarPadrao, 0, wx.ALL, 5)
		hbox.AddStretchSpacer()
		hbox.Add(btnFechar, 0, wx.ALL, 5)
		vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, 5)

		dlg.SetSizerAndFit(vbox)
		dlg.CenterOnParent()
		self._bind_global_shortcuts_to_dialog(dlg)

		def refreshList():
			lst.Clear()
			nomes = self.bibleManager.listar_nomes()
			if nomes:
				lst.AppendItems(nomes)
			if self.versaoAtual in nomes:
				lst.SetSelection(nomes.index(self.versaoAtual))

		def onImportar(e):
			fd = wx.FileDialog(dlg, "Escolha um arquivo de Bíblia (.json)", wildcard="JSON (*.json)|*.json",
				style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
			self._bind_global_shortcuts_to_dialog(fd)
			if fd.ShowModal() == wx.ID_OK:
				origem = fd.GetPath()
				try:
					self.bibleManager.adicionar_arquivo_json(origem)
					refreshList()
					if ui:
						ui.message("Bíblia importada com sucesso.")
					if not self.versaoAtual:
						nomes = self.bibleManager.listar_nomes()
						if nomes:
							versao_nova = nomes[0]
							try:
								biblia = self.bibleManager.carregar(versao_nova)
								nm = NotesManager(versao_nova)
								self.biblia = biblia
								self.notas = nm.all()
								self.notesManager = nm
								self.versaoAtual = versao_nova
								self.configManager.set_version(versao_nova)
								self._buildNotesIndex()
								self.mostrarLivros()
								dlg.Close()
								if ui:
									ui.message(f"Versão {versao_nova} carregada. Selecione um livro.")
							except Exception as err2:
								wx.MessageBox(f"Bíblia importada, mas houve erro ao carregar: {err2}", "Aviso", wx.OK | wx.ICON_WARNING)
				except Exception as err:
					wx.MessageBox(f"Falha ao importar: {err}", "Erro", wx.OK | wx.ICON_ERROR)
			fd.Destroy()

		def onRemover(e):
			idx = lst.GetSelection()
			if idx == wx.NOT_FOUND:
				wx.MessageBox("Selecione uma versão para remover.", "Aviso", wx.OK | wx.ICON_INFORMATION)
				return
			versao = lst.GetString(idx)
			if versao == self.versaoAtual:
				wx.MessageBox("Não é possível remover a versão atualmente carregada.", "Aviso", wx.OK | wx.ICON_WARNING)
				return
			if wx.MessageBox(f"Remover a versão '{versao}'?", "Confirmar", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
				try:
					self.bibleManager.remover_versao(versao)
					refreshList()
					if ui:
						ui.message("Versão removida.")
				except Exception as err:
					wx.MessageBox(f"Falha ao remover: {err}", "Erro", wx.OK | wx.ICON_ERROR)

		def onTornarPadrao(e):
			idx = lst.GetSelection()
			if idx == wx.NOT_FOUND:
				wx.MessageBox("Selecione uma versão para tornar padrão.", "Aviso", wx.OK | wx.ICON_INFORMATION)
				return
			versao = lst.GetString(idx)
			try:
				self.configManager.set_version(versao)
				biblia = self.bibleManager.carregar(versao)
				nm = NotesManager(versao)
				self.biblia = biblia
				self.notas = nm.all()
				self.notesManager = nm
				self.versaoAtual = versao
				self._buildNotesIndex()
				self._ultimoLivroSelecionado = None
				self._ultimoCapituloSelecionado = None
				self.mostrarLivros()
				if ui:
					ui.message(f"Versão atual: {versao}")
				dlg.Close()
			except Exception as err:
				wx.MessageBox(f"Falha ao carregar versão: {err}", "Erro", wx.OK | wx.ICON_ERROR)

		btnImportar.Bind(wx.EVT_BUTTON, onImportar)
		btnRemover.Bind(wx.EVT_BUTTON, onRemover)
		btnBaixar.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://drive.google.com/drive/folders/1THS2L9GiCx_rWWCJ23JGh3Ws7qVup0uE?usp=sharing"))
		btnTornarPadrao.Bind(wx.EVT_BUTTON, onTornarPadrao)
		btnFechar.Bind(wx.EVT_BUTTON, lambda e: dlg.Close())

		refreshList()
		dlg.ShowModal()
		dlg.Destroy()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		self._frame = None
		self.menuItem = None

		if gui and hasattr(gui, "mainFrame") and hasattr(gui.mainFrame, "sysTrayIcon"):
			try:
				if hasattr(gui.mainFrame.sysTrayIcon, "toolsMenu"):
					self.menuItem = gui.mainFrame.sysTrayIcon.toolsMenu.Append(wx.ID_ANY, "Open Bible", "Abre o leitor da Bíblia")
					gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onMenuAbrir, self.menuItem)
			except Exception:
				pass

		cm = ConfigManager()
		if cm.get_speak_on_startup():
			wx.CallLater(1500, self._speakRandomFavorite)

	def _speakRandomFavorite(self):
		favm = FavoritesManager()
		favoritos = favm.all()
		if favoritos:
			fav = random.choice(favoritos)
			livro_nome = NOMES_LIVROS.get(fav["livro"], fav["livro"])
			referencia = f"{livro_nome} {fav['capitulo']}:{fav['versiculo']}"
			speech.speakMessage(f"{fav['texto']} — {referencia}")

	def terminate(self):
		try:
			if self.menuItem and gui and hasattr(gui.mainFrame, "sysTrayIcon"):
				if hasattr(gui.mainFrame.sysTrayIcon, "toolsMenu"):
					gui.mainFrame.sysTrayIcon.toolsMenu.Delete(self.menuItem.GetId())
		except Exception:
			pass

		try:
			if self._frame:
				if self._frame.leituraTimer.IsRunning():
					self._frame.leituraTimer.Stop()
				for t in (getattr(self._frame, '_txtUpdateTimer', None), getattr(self._frame, '_savePositionTimer', None)):
					try:
						if t and t.IsRunning():
							t.Stop()
					except Exception:
						pass
				if self._frame.IsShown():
					self._frame.Destroy()
		except Exception:
			pass
		self._frame = None

	def onMenuAbrir(self, evt):
		self._iniciar_interface()

	def _iniciar_interface(self):
		try:
			if self._frame and self._frame.IsShown():
				try:
					self._frame.Raise()
					self._frame.SetFocus()
					wx.CallAfter(self._frame._ensureListFocus)
					return
				except Exception:
					try:
						self._frame.Destroy()
					except Exception:
						pass
					self._frame = None

			cm = ConfigManager()
			bm = BibleManager(PLUGIN_BASE_DIR)
			favm = FavoritesManager()

			if not bm.has_versions():
				if ui:
					ui.message("Open Bible: Nenhuma Bíblia encontrada.")

				def _mostrar_aviso_sem_biblia():
					try:
						parent = gui.mainFrame if (gui and hasattr(gui, "mainFrame")) else None
						dlg = wx.Dialog(parent, title="Open Bible \u2013 Sem B\u00edblia", style=wx.DEFAULT_DIALOG_STYLE)
						vbox = wx.BoxSizer(wx.VERTICAL)

						lbl = wx.StaticText(dlg, label=(
							"Nenhuma B\u00edblia foi encontrada na pasta do addon.\n\n"
							"Para usar o Open Bible voc\u00ea precisa baixar ao menos\n"
							"um arquivo de B\u00edblia (.json) e import\u00e1-lo pelo\n"
							"Gerenciador de B\u00edblias (Ctrl+G).\n\n"
							"Deseja abrir o Google Drive para baixar as B\u00edblias agora?"
						))
						vbox.Add(lbl, 0, wx.ALL, 14)

						hbox = wx.BoxSizer(wx.HORIZONTAL)
						btnSim = wx.Button(dlg, wx.ID_YES, "Sim, baixar agora")
						btnNao = wx.Button(dlg, wx.ID_NO, "N\u00e3o")
						btnSim.SetDefault()
						hbox.Add(btnSim, 0, wx.ALL, 5)
						hbox.Add(btnNao, 0, wx.ALL, 5)
						vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

						dlg.SetSizerAndFit(vbox)
						dlg.CenterOnScreen()

						def _onSim(e): dlg.EndModal(wx.ID_YES)
						def _onNao(e): dlg.EndModal(wx.ID_NO)
						btnSim.Bind(wx.EVT_BUTTON, _onSim)
						btnNao.Bind(wx.EVT_BUTTON, _onNao)

						def _charHook(e):
							if e.GetKeyCode() == wx.WXK_ESCAPE:
								dlg.EndModal(wx.ID_NO)
								return
							e.Skip()
						dlg.Bind(wx.EVT_CHAR_HOOK, _charHook)

						res = dlg.ShowModal()
						dlg.Destroy()

						if res == wx.ID_YES:
							webbrowser.open("https://drive.google.com/drive/folders/1THS2L9GiCx_rWWCJ23JGh3Ws7qVup0uE?usp=sharing")


						frame_vazio = BibliaFrame([], [], bm, NotesManager(""), None, cm, favm)
						frame_vazio.Show()
						frame_vazio.Raise()
						frame_vazio.SetFocus()
						wx.CallAfter(frame_vazio._ensureListFocus)
						if ui:
							ui.message("Open Bible aberto. Use Ctrl+G para abrir o Gerenciador de B\u00edblias e importar um arquivo JSON.")
					except Exception:
						pass

				wx.CallAfter(_mostrar_aviso_sem_biblia)
				return

			versao = cm.get_version()
			if not versao:
				nomes = bm.listar_nomes()
				versao = nomes[0]
				cm.set_version(versao)

			try:
				biblia = bm.carregar(versao)
			except Exception as e:
				biblia = []
				if ui:
					ui.message(f"Erro ao carregar versão '{versao}': {e}")

			nm = NotesManager(versao)
			notas = nm.all()

			self._frame = BibliaFrame(biblia, notas, bm, nm, versao, cm, favm)
			self._frame.Show()
			self._frame.Raise()
			self._frame.SetFocus()
			wx.CallAfter(self._frame._ensureListFocus)
		except Exception as e:
			wx.MessageBox(f"Erro crítico ao iniciar o Open Bible: {e}", "Erro", wx.OK | wx.ICON_ERROR)

	@script(
		description="Abrir Open Bible",
		category="Open Bible",
		gesture="kb:control+alt+b"
	)
	def script_openBible(self, gesture):
		self._iniciar_interface()
